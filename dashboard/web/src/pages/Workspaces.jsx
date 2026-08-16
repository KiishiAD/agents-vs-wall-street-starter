import React from "react";
import { Link } from "react-router-dom";
import { useLive } from "../live.jsx";
import { Sparkline, Gauge, DirArrow, pct, timeAgo } from "../ui.jsx";

export default function Workspaces() {
  const { data: companies, loading } = useLive("/api/companies");

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Workspaces</h1>
          <p className="muted">
            Each workspace runs a fleet of forecasting agents that collect signals and vote on a consensus outcome.
          </p>
        </div>
      </div>

      {loading && <div className="muted">Loading workspaces…</div>}

      <div className="grid">
        {(companies || []).map((c) => {
          const hist = c.forecast?.history?.slice(-30).map((h) => h.p) || [];
          return (
            <Link to={`/c/${c.id}`} key={c.id} className="card company-card">
              <div className="company-card-top">
                <div>
                  <div className="company-name">
                    {c.name} <span className="ticker">{c.ticker}</span>
                  </div>
                  <div className="sector">{c.sector}</div>
                </div>
                <div className="consensus-num">
                  <span className="big">{pct(c.forecast?.consensus ?? 0)}</span>
                  <DirArrow direction={c.forecast?.direction} />
                </div>
              </div>

              <div className="question">{c.question}</div>

              <div className="company-card-spark">
                <Sparkline values={hist} w={320} h={44} />
              </div>

              <div className="company-card-foot">
                <span className="stat">
                  <b>{c.runningAgents}</b>/{c.agentCount} agents live
                </span>
                <span className="stat">
                  <b>{c.signalCount}</b> signals
                </span>
                <span className="stat">
                  conf <b>{pct(c.forecast?.confidence ?? 0)}</b>
                </span>
                <span className="stat muted">{timeAgo(c.forecast?.updatedAt)}</span>
              </div>

              {c.runningAgents > 0 && <span className="pulse-tag">● {c.activeRuns} running</span>}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
