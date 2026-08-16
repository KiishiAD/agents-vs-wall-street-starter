import React from "react";
import { Link, useParams } from "react-router-dom";
import { useLive, matchSlug } from "../live.jsx";
import {
  AreaChart,
  Gauge,
  DirArrow,
  StanceBadge,
  StatusDot,
  Sparkline,
  Weight,
  pct,
  pct1,
  timeAgo,
} from "../ui.jsx";

export default function Company() {
  const { slug } = useParams();
  const { data, loading } = useLive(`/api/companies/${slug}`, {
    match: matchSlug(slug),
    deps: [slug],
  });

  if (loading && !data) return <div className="page muted">Loading {slug}…</div>;
  if (!data) return <div className="page">Company not found.</div>;

  const { company, forecast, signals, agents, runs } = data;
  const activeRuns = runs.filter((r) => r.status === "running");

  return (
    <div className="page">
      <div className="crumbs">
        <Link to="/">Workspaces</Link> <span>/</span> <b>{company.name}</b>
      </div>

      <div className="company-hero card">
        <div className="hero-left">
          <div className="company-name lg">
            {company.name} <span className="ticker">{company.ticker}</span>
          </div>
          <div className="sector">{company.sector} · forecasting {company.period}</div>
          <div className="question lg">{company.question}</div>
          <p className="muted">{company.description}</p>

          {company.metrics?.length > 0 && (
            <div className="metrics-strip">
              {company.metrics.map((m) => (
                <div className="metric-target" key={m.label}>
                  <span className="metric-label">{m.label}</span>
                  <span className="metric-val">
                    {m.consensus?.toLocaleString()} <span className="metric-unit">{m.units}</span>
                  </span>
                  <span className="metric-tag">consensus</span>
                </div>
              ))}
            </div>
          )}

          <div className="rationale">
            <span className="label">consensus rationale</span>
            {forecast?.rationale}
          </div>
          {company.corpusDocs?.length > 0 && (
            <div className="corpus-note muted sm">
              corpus: {company.corpusDocs.length} recent docs · e.g. <code>{company.corpusDocs[0]}</code>
            </div>
          )}
        </div>
        <div className="hero-right">
          <Gauge value={forecast?.consensus ?? 0.5} confidence={forecast?.confidence} size={200} />
          <div className="hero-dir">
            <DirArrow direction={forecast?.direction} /> updated {timeAgo(forecast?.updatedAt)}
          </div>
        </div>
      </div>

      <div className="section">
        <div className="section-head">
          <h2>Consensus trend</h2>
          <span className="muted">{forecast?.history?.length || 0} points</span>
        </div>
        <div className="card chart-card">
          <AreaChart points={forecast?.history || []} field="p" w={900} h={200} />
        </div>
      </div>

      <div className="two-col">
        <div className="section">
          <div className="section-head">
            <h2>Agents</h2>
            <span className="muted">{agents.filter((a) => a.status === "running").length} running</span>
          </div>
          <div className="agent-list">
            {agents.map((a) => {
              const run = a.currentRunId
                ? runs.find((r) => r.id === a.currentRunId)
                : runs.find((r) => r.agentId === a.id);
              const target = run ? `/c/${slug}/runs/${run.id}` : null;
              const inner = (
                <>
                  <StatusDot status={a.status} />
                  <div className="agent-main">
                    <div className="agent-name">
                      {a.name}
                      {a.isConsensus && <span className="tag">consensus</span>}
                    </div>
                    <div className="agent-role muted">{a.role}</div>
                    {run && (
                      <div className="agent-run muted">
                        {run.status === "running" ? "▶ running: " : "last: "}
                        {run.summary || run.signalTitle || "working…"}
                      </div>
                    )}
                  </div>
                  <div className="agent-meta">
                    <span className={`chip chip-${a.status}`}>{a.status}</span>
                    <span className="muted sm">{timeAgo(a.lastActiveAt)}</span>
                  </div>
                </>
              );
              return target ? (
                <Link to={target} key={a.id} className="agent-row link">
                  {inner}
                </Link>
              ) : (
                <div key={a.id} className="agent-row">
                  {inner}
                </div>
              );
            })}
          </div>
        </div>

        <div className="section">
          <div className="section-head">
            <h2>Signals</h2>
            <span className="muted">{signals.length} tracked</span>
          </div>
          <div className="signal-list">
            {signals.map((s) => (
              <Link to={`/c/${slug}/signals/${s.id}`} key={s.id} className="card signal-card">
                <div className="signal-top">
                  <div>
                    <div className="signal-title">{s.title}</div>
                    <div className="signal-cat muted">{s.category}</div>
                  </div>
                  <StanceBadge stance={s.stance} />
                </div>
                <div className="signal-mid">
                  <div className="signal-value">
                    {s.value}
                    <span className="unit"> {s.unit}</span>
                  </div>
                  <Sparkline
                    values={(s.valueHistory || []).slice(-24).map((h) => h.value)}
                    w={130}
                    h={34}
                    stroke={s.stance === "bearish" ? "var(--down)" : "var(--up)"}
                  />
                </div>
                <div className="signal-foot">
                  <span className="muted sm">implied {pct(s.p)}</span>
                  <Weight value={s.weight} />
                  <span className="muted sm">{timeAgo(s.updatedAt)}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="section">
        <div className="section-head">
          <h2>Recent runs</h2>
          <span className="muted">{activeRuns.length} active</span>
        </div>
        <div className="run-table card">
          {runs.slice(0, 12).map((r) => (
            <Link to={`/c/${slug}/runs/${r.id}`} key={r.id} className="run-row">
              <StatusDot status={r.status} />
              <span className="run-agent">{r.agentName}</span>
              <span className="run-signal muted">{r.signalTitle || "—"}</span>
              <span className="run-summary muted">{r.summary || (r.status === "running" ? "in progress…" : "")}</span>
              <span className="run-time muted sm">{timeAgo(r.startedAt)}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
