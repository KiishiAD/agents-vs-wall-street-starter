#!/usr/bin/env python3
"""Run each test module in parallel — one subprocess per part.

Dependency-free: discovers `tests/test_*.py` and runs each in its own
`unittest` subprocess concurrently, then aggregates. Fast feedback, and one
crashing module can't take the others down.

    python3 scripts/test_parallel.py
    python3 scripts/test_parallel.py --workers 4
    python3 scripts/test_parallel.py test_pipeline test_run   # subset
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"


def _discover() -> list[str]:
    return sorted(p.stem for p in TESTS_DIR.glob("test_*.py"))


def _run_module(module: str) -> tuple[str, int, str, float]:
    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", f"{module}.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return module, proc.returncode, proc.stdout + proc.stderr, time.perf_counter() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run each test module in parallel.")
    parser.add_argument("modules", nargs="*", help="Specific test modules (default: all).")
    parser.add_argument("--workers", type=int, default=0, help="Parallel workers (default: 0 = one per module).")
    args = parser.parse_args(argv)

    modules = args.modules or _discover()
    if not modules:
        print("no test modules found", file=sys.stderr)
        return 2
    workers = args.workers if args.workers > 0 else len(modules)

    print(f"running {len(modules)} test module(s) on {workers} worker(s)\n")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_run_module, modules))

    failed = []
    for module, code, output, elapsed in results:
        status = "ok  " if code == 0 else "FAIL"
        print(f"[{status}] tests.{module}  ({elapsed:.2f}s)")
        if code != 0:
            failed.append(module)
            print("\n".join("    " + line for line in output.strip().splitlines()))

    passed = len(results) - len(failed)
    print(f"\n{passed}/{len(results)} module(s) passed" + (f" — failed: {', '.join(failed)}" if failed else ""))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
