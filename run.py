"""One-command, config-driven forecast run.

Declare the numbers you want in a config file (`forecasts.json` by default):
each *job* names a company profile, a target metric and the source-backed
observations to resolve. This runner loads each profile, runs the four-agent
pipeline (initialiser → signal extractor → analyst consensus) over the
deterministic engine, and returns the forecast values.

    python3 run.py                          # run every configured job
    python3 run.py --company ADI            # filter by ticker / company id
    python3 run.py --metric ADI_REVENUE_FY2026Q3
    python3 run.py --json                   # machine-readable values on stdout
    python3 run.py --write-traces           # also refresh each job's dashboard trace
    python3 run.py --retries 3              # attempts per step on transient failure
    python3 run.py --config path/to/other.json

Resilience: every job is isolated. A step that hits a *transient* error is
retried with backoff; a single *bad observation* (e.g. a quotation that no
longer verifies) is dropped so the rest of the signal map still produces a
number (a "degraded" run); and any job that still cannot produce a value is
recorded as "failed" and the batch keeps going. The process exits non-zero if
any job failed or failed its challenge, so `python3 run.py` is safe to gate a
submission on — but it never aborts halfway.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from forecasting import run_pipeline, write_run_receipt

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "forecasts.json"
DEFAULT_OUT_DIR = ROOT / "build"
DEFAULT_RETRIES = 2


class RunConfigError(ValueError):
    pass


def _retry(
    fn: Callable[[], Any],
    *,
    retries: int,
    delay: float,
    label: str,
    log: Callable[[str], None],
) -> Any:
    """Run `fn`, retrying up to `retries` times with linear backoff.

    Deterministic validation errors will not "heal" on retry, but transient
    ones (I/O now; model/network calls in a future live version) will. Callers
    that want graceful degradation instead of a raise catch the final error.
    """
    attempts = retries + 1
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as error:  # noqa: BLE001 - isolate + retry, never abort the batch
            last = error
            if attempt < attempts:
                log(f"    · {label}: attempt {attempt}/{attempts} failed ({error}); retrying")
                time.sleep(delay * attempt)
    assert last is not None
    raise last


def _run_job(
    job: dict[str, Any],
    *,
    out_dir: Path,
    write_traces: bool,
    retries: int,
    delay: float,
    log: Callable[[str], None],
) -> dict[str, Any]:
    """Run one job in isolation. Never raises — failures come back as a row.

    The pipeline builds the profile and resolves the signals itself; a single
    bad signal is healed (dropped) inside the extractor, so a raise here means
    the job could not produce a number at all (e.g. no valid anchor)."""
    job_id = job.get("id", "?")
    log(f"  ▸ {job_id}")
    try:
        run_result = _retry(
            lambda: run_pipeline(
                ROOT / job["profile"], job["metric"], job.get("observations", []), repository_root=ROOT
            ),
            retries=retries,
            delay=delay,
            label=f"run {job_id}",
            log=log,
        )
    except Exception as error:  # noqa: BLE001 - isolate the job, keep the batch going
        log(f"    ! {job_id} failed after retries: {error}")
        return {
            "id": job_id,
            "status": "failed",
            "metric": job.get("metric"),
            "profile": job.get("profile"),
            "error": str(error),
            "challengePassed": False,
        }

    profile = run_result.profile
    result = run_result.result
    challenge = run_result.challenge
    pipeline = run_result.trace
    dropped = list(run_result.dropped)
    for entry in dropped:
        log(f"    · healed (dropped signal) {entry['signalId']}: {entry['reason']}")

    receipt_path = out_dir / f"{job_id}-receipt.json"
    write_run_receipt(profile, result, challenge, receipt_path, pipeline=pipeline)
    if write_traces and job.get("trace"):
        write_run_receipt(profile, result, challenge, ROOT / job["trace"], pipeline=pipeline)

    warnings = sum(1 for i in challenge.issues if i.severity == "warning")
    errors = sum(1 for i in challenge.issues if i.severity == "error")
    discarded = sum(e.discarded for e in pipeline.extractions)
    search = pipeline.evidence_search
    return {
        "id": job_id,
        "status": "degraded" if dropped else "ok",
        "searchProvider": search.get("provider"),
        "searchMode": search.get("mode"),
        "searchQueries": len(search.get("queries", ())),
        "searchHits": sum(q.get("results", 0) for q in search.get("queries", ())),
        "company": profile.company.name,
        "ticker": profile.company.ticker,
        "metric": result.metric_id,
        "period": result.period,
        "units": result.units,
        "downside": str(result.base_range.low),
        "base": str(result.base_forecast),
        "upside": str(result.base_range.high),
        "formula": result.formula,
        "consensus": pipeline.analyst.consensus_forecast,
        "agreement": pipeline.analyst.agreement,
        "subagentsPerSignal": pipeline.subagents_per_signal,
        "biasedDiscarded": discarded,
        "droppedSignals": dropped,
        "challengePassed": challenge.passed,
        "warnings": warnings,
        "errors": errors,
        "receipt": str(receipt_path),
    }


def _matches(job: dict[str, Any], company: str | None, metric: str | None) -> bool:
    if metric and job.get("metric") != metric:
        return False
    if company:
        needle = company.lower()
        hay = f"{job.get('id', '')} {job.get('profile', '')} {job.get('metric', '')}".lower()
        if needle not in hay:
            return False
    return True


def _safe_run_job(job: dict[str, Any], *, log: Callable[[str], None], **kwargs) -> dict[str, Any]:
    """_run_job never raises; this is a belt-and-braces guard so even a bug in
    reporting one job can never abort the whole batch."""
    try:
        return _run_job(job, log=log, **kwargs)
    except Exception as error:  # noqa: BLE001
        return {"id": job.get("id", "?"), "status": "failed", "error": str(error), "challengePassed": False}


def _auto_workers(n_jobs: int, requested: int) -> int:
    if requested and requested > 0:
        return min(requested, n_jobs)
    return min(n_jobs, os.cpu_count() or 4)  # 0 / unset -> auto


def run(
    config_path: Path,
    *,
    company: str | None = None,
    metric: str | None = None,
    out_dir: Path = DEFAULT_OUT_DIR,
    write_traces: bool = False,
    retries: int = DEFAULT_RETRIES,
    delay: float = 0.5,
    workers: int = 0,
    log: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    log = log or (lambda _msg: None)
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    all_jobs = config.get("jobs", [])
    jobs = [j for j in all_jobs if _matches(j, company, metric)]
    if not jobs:
        # A filter that matches nothing is benign (the company just isn't wired
        # yet) — return no rows so a per-company launcher exits cleanly. Only an
        # empty/misconfigured config with no filter is a hard error.
        if company or metric:
            log(f"no forecast jobs configured yet for filter (company={company!r}, metric={metric!r})")
            return []
        raise RunConfigError(f"no jobs configured in {config_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    job_kwargs = dict(out_dir=out_dir, write_traces=write_traces, retries=retries, delay=delay)

    n_workers = _auto_workers(len(jobs), workers)
    if n_workers <= 1 or len(jobs) == 1:
        return [_safe_run_job(j, log=log, **job_kwargs) for j in jobs]

    # Parallel: each job is independent and isolated. Buffer each job's log
    # lines and flush them together on completion so parallel output stays
    # readable, and reassemble rows in config order for deterministic output.
    log(f"running {len(jobs)} jobs on {n_workers} workers")
    rows: list[dict[str, Any] | None] = [None] * len(jobs)

    def task(index: int, job: dict[str, Any]):
        buffer: list[str] = []
        row = _safe_run_job(job, log=buffer.append, **job_kwargs)
        return index, row, buffer

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = [pool.submit(task, i, j) for i, j in enumerate(jobs)]
        for future in as_completed(futures):
            index, row, buffer = future.result()
            for line in buffer:
                log(line)
            rows[index] = row
    return [r for r in rows if r is not None]


def _print_human(rows: list[dict[str, Any]]) -> None:
    for r in rows:
        if r.get("status") == "failed":
            print(f"\n{r.get('id')} · {r.get('metric', '?')}")
            print(f"  status                   : FAILED — {r.get('error')}")
            continue
        status = "PASS" if r["challengePassed"] else "FAIL"
        tag = "" if r["status"] == "ok" else "  [degraded]"
        print(f"\n{r['ticker']} · {r['metric']} ({r['period']}){tag}")
        print(f"  downside / base / upside : {r['downside']} / {r['base']} / {r['upside']} {r['units']}")
        print(f"  formula                  : {r['formula']}")
        print(f"  consensus                : {r['consensus']} {r['units']}  ({r['agreement']})")
        hits = f", {r['searchHits']} hits" if r.get("searchHits") else ""
        print(f"  evidence search          : {r.get('searchProvider')} · {r.get('searchQueries')} quer{'y' if r.get('searchQueries')==1 else 'ies'}{hits} ({r.get('searchMode')})")
        print(f"  extractor                : {r['subagentsPerSignal']} sub-agents/signal, {r['biasedDiscarded']} biased discarded")
        for d in r.get("droppedSignals", []):
            print(f"  healed (dropped signal)  : {d['signalId']} — {d['reason']}")
        print(f"  challenge                : {status} ({r['warnings']} warning(s), {r['errors']} error(s))")
        print(f"  receipt                  : {r['receipt']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the configured forecast pipeline and return the numbers.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to the run config (default: forecasts.json).")
    parser.add_argument("--company", help="Only run jobs matching this ticker / company id / job id.")
    parser.add_argument("--metric", help="Only run the job for this exact metric id.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Where to write receipts (default: build/).")
    parser.add_argument("--write-traces", action="store_true", help="Also refresh each job's dashboard trace file.")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Retries per step on transient failure (default: 2).")
    parser.add_argument("--retry-delay", type=float, default=0.5, help="Base backoff between retries, seconds (default: 0.5).")
    parser.add_argument("--workers", type=int, default=0, help="Run jobs in parallel across N workers (default: 0 = auto per CPU; 1 = sequential).")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit the values as JSON on stdout.")
    args = parser.parse_args(argv)

    # Progress goes to stderr so --json stdout stays clean and pipeable.
    log = (lambda msg: None) if args.as_json else (lambda msg: print(msg, file=sys.stderr))

    try:
        rows = run(
            args.config,
            company=args.company,
            metric=args.metric,
            out_dir=args.out_dir,
            write_traces=args.write_traces,
            retries=max(0, args.retries),
            delay=max(0.0, args.retry_delay),
            workers=args.workers,
            log=log,
        )
    except (RunConfigError, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    elif not rows:
        target = args.company or args.metric or "the config"
        print(f"nothing to run for {target!r} — no forecast jobs configured yet.")
    else:
        _print_human(rows)

    failed = [r for r in rows if r.get("status") == "failed" or not r.get("challengePassed")]
    if failed and not args.as_json:
        print(f"\n{len(failed)} of {len(rows)} job(s) did not pass.", file=sys.stderr)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
