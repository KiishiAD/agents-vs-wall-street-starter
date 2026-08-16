import React from "react";
import { Link, useParams } from "react-router-dom";
import { useLive, matchSlug } from "../live.jsx";
import { AreaChart, StanceBadge, StatusDot, Weight, pct, timeAgo } from "../ui.jsx";

export default function Signal() {
  const { slug, signalId } = useParams();
  const { data: signal } = useLive(`/api/companies/${slug}/signals/${signalId}`, {
    match: (e) => e.slug === slug && e.path.includes(signalId),
    deps: [slug, signalId],
  });
  const { data: bundle } = useLive(`/api/companies/${slug}`, {
    match: matchSlug(slug),
    deps: [slug],
  });

  if (!signal) return <div className="page muted">Loading signal…</div>;

  const agents = (bundle?.agents || []).filter((a) => (a.signalIds || []).includes(signalId));
  const runs = (bundle?.runs || []).filter((r) => r.signalId === signalId);

  return (
    <div className="page">
      <div className="crumbs">
        <Link to="/">Workspaces</Link> <span>/</span>
        <Link to={`/c/${slug}`}>{bundle?.company?.name || slug}</Link> <span>/</span>
        <b>{signal.title}</b>
      </div>

      <div className="signal-hero card">
        <div>
          <div className="signal-cat muted">{signal.category}</div>
          <h1>{signal.title}</h1>
          <p className="muted">{signal.description}</p>
          <div className="kv-row">
            <div className="kv">
              <span className="label">current</span>
              <b>
                {signal.value} <span className="unit">{signal.unit}</span>
              </b>
            </div>
            <div className="kv">
              <span className="label">implied prob.</span>
              <b>{pct(signal.p)}</b>
            </div>
            <div className="kv">
              <span className="label">confidence</span>
              <b>{pct(signal.confidence)}</b>
            </div>
            <div className="kv">
              <span className="label">stance</span>
              <StanceBadge stance={signal.stance} />
            </div>
            <div className="kv">
              <span className="label">weight</span>
              <Weight value={signal.weight} />
            </div>
          </div>
          <div className="rationale">
            <span className="label">sources</span>
            {signal.source}
          </div>
        </div>
      </div>

      <div className="two-col">
        <div className="section">
          <div className="section-head">
            <h2>Metric history</h2>
          </div>
          <div className="card chart-card">
            <AreaChart points={signal.valueHistory || []} field="value" w={560} h={180} format={(v) => v} />
          </div>
        </div>
        <div className="section">
          <div className="section-head">
            <h2>Implied probability</h2>
          </div>
          <div className="card chart-card">
            <AreaChart points={signal.history || []} field="p" w={560} h={180} />
          </div>
        </div>
      </div>

      <div className="two-col">
        <div className="section">
          <div className="section-head">
            <h2>Agents on this signal</h2>
          </div>
          <div className="agent-list">
            {agents.map((a) => (
              <div key={a.id} className="agent-row">
                <StatusDot status={a.status} />
                <div className="agent-main">
                  <div className="agent-name">{a.name}</div>
                  <div className="agent-role muted">{a.role}</div>
                </div>
                <span className={`chip chip-${a.status}`}>{a.status}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="section">
          <div className="section-head">
            <h2>Runs for this signal</h2>
          </div>
          <div className="run-table card">
            {runs.slice(0, 10).map((r) => (
              <Link to={`/c/${slug}/runs/${r.id}`} key={r.id} className="run-row">
                <StatusDot status={r.status} />
                <span className="run-agent">{r.agentName}</span>
                <span className="run-summary muted">{r.summary || (r.status === "running" ? "in progress…" : "")}</span>
                <span className="run-time muted sm">{timeAgo(r.startedAt)}</span>
              </Link>
            ))}
            {runs.length === 0 && <div className="muted pad">No runs yet.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
