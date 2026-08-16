import React, { useEffect, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { useLive } from "../live.jsx";
import { StatusDot, pct, timeAgo } from "../ui.jsx";

const LEVEL_CLASS = { info: "l-info", tool: "l-tool", result: "l-result", warn: "l-warn", error: "l-error" };

export default function Run() {
  const { slug, runId } = useParams();
  const { data: run } = useLive(`/api/companies/${slug}/runs/${runId}`, {
    match: (e) => e.slug === slug && e.path.includes(runId),
    deps: [slug, runId],
    throttle: 120,
  });
  const consoleRef = useRef(null);
  const log = run?.log || [];

  // Auto-scroll to bottom as new lines stream in.
  useEffect(() => {
    const el = consoleRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [log.length]);

  if (!run) return <div className="page muted">Loading run…</div>;

  const dur = run.endedAt
    ? Math.round((new Date(run.endedAt) - new Date(run.startedAt)) / 1000)
    : Math.round((Date.now() - new Date(run.startedAt)) / 1000);

  return (
    <div className="page">
      <div className="crumbs">
        <Link to="/">Workspaces</Link> <span>/</span>
        <Link to={`/c/${slug}`}>{slug}</Link> <span>/</span>
        <b>{run.agentName}</b>
      </div>

      <div className="run-hero card">
        <div>
          <div className="run-hero-title">
            <StatusDot status={run.status} />
            {run.agentName}
            <span className={`chip chip-${run.status}`}>{run.status}</span>
          </div>
          <div className="muted">
            signal: <b>{run.signalTitle || "all signals"}</b> · trigger {run.trigger} · started {timeAgo(run.startedAt)} · {dur}s
          </div>
          {run.summary && <div className="run-summary-big">{run.summary}</div>}
        </div>
        {run.result && (
          <div className="run-result">
            <span className="label">result</span>
            <pre>{JSON.stringify(run.result, null, 2)}</pre>
          </div>
        )}
      </div>

      <div className="section">
        <div className="section-head">
          <h2>Live trace</h2>
          <span className="muted">
            {log.length} lines {run.status === "running" && <span className="blink">● streaming</span>}
          </span>
        </div>
        <div className="console" ref={consoleRef}>
          {log.map((l, i) => (
            <div key={i} className={`logline ${LEVEL_CLASS[l.level] || "l-info"}`}>
              <span className="log-t">{new Date(l.t).toLocaleTimeString()}</span>
              <span className="log-phase">{l.phase}</span>
              <span className="log-msg">
                {l.message}
                {l.data && <span className="log-data"> {JSON.stringify(l.data)}</span>}
              </span>
            </div>
          ))}
          {run.status === "running" && (
            <div className="logline l-cursor">
              <span className="log-t" />
              <span className="log-phase" />
              <span className="log-msg cursor">▋</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
