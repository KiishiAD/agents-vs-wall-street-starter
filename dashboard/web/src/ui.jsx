import React from "react";
import { useLiveStatus } from "./live.jsx";

export const pct = (p) => `${(p * 100).toFixed(0)}%`;
export const pct1 = (p) => `${(p * 100).toFixed(1)}%`;

export function timeAgo(iso) {
  if (!iso) return "—";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function StanceBadge({ stance }) {
  const cls = stance === "bullish" ? "up" : stance === "bearish" ? "down" : "flat";
  return <span className={`badge badge-${cls}`}>{stance || "neutral"}</span>;
}

export function StatusDot({ status }) {
  const map = { running: "running", completed: "ok", idle: "idle", error: "err" };
  return <span className={`dot dot-${map[status] || "idle"}`} title={status} />;
}

export function DirArrow({ direction }) {
  if (direction === "up") return <span className="dir up">▲</span>;
  if (direction === "down") return <span className="dir down">▼</span>;
  return <span className="dir flat">▬</span>;
}

// Small inline sparkline from an array of numbers.
export function Sparkline({ values, w = 120, h = 30, stroke = "var(--accent)", fill = true }) {
  if (!values || values.length < 2) return <svg width={w} height={h} />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = w / (values.length - 1);
  const pts = values.map((v, i) => [i * step, h - ((v - min) / span) * (h - 4) - 2]);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const area = `${line} L${w},${h} L0,${h} Z`;
  return (
    <svg width={w} height={h} className="spark">
      {fill && <path d={area} fill={stroke} opacity="0.12" />}
      <path d={line} fill="none" stroke={stroke} strokeWidth="1.6" />
    </svg>
  );
}

// Larger area chart for history [{t, p|value}].
export function AreaChart({ points, field = "p", w = 640, h = 180, format = pct }) {
  if (!points || points.length < 2) return <div className="chart-empty">gathering data…</div>;
  const vals = points.map((d) => d[field]);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = max - min || 1;
  const padY = 16;
  const step = w / (points.length - 1);
  const y = (v) => h - padY - ((v - min) / span) * (h - padY * 2);
  const pts = vals.map((v, i) => [i * step, y(v)]);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const area = `${line} L${w},${h} L0,${h} Z`;
  const last = vals[vals.length - 1];
  const first = vals[0];
  const rising = last >= first;
  const color = rising ? "var(--up)" : "var(--down)";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="areachart" preserveAspectRatio="none">
      <defs>
        <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((g) => (
        <line key={g} x1="0" x2={w} y1={padY + g * (h - padY * 2)} y2={padY + g * (h - padY * 2)} className="grid" />
      ))}
      <path d={area} fill="url(#ag)" />
      <path d={line} fill="none" stroke={color} strokeWidth="2" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="3.5" fill={color} />
    </svg>
  );
}

// Circular gauge for a 0..1 probability.
export function Gauge({ value = 0.5, confidence, size = 160 }) {
  const r = size / 2 - 12;
  const c = size / 2;
  const circ = Math.PI * r; // half circle
  const dash = circ * value;
  const color = value >= 0.6 ? "var(--up)" : value <= 0.4 ? "var(--down)" : "var(--warn)";
  return (
    <div className="gauge" style={{ width: size }}>
      <svg width={size} height={size / 2 + 24}>
        <path d={arc(c, c, r, 180, 360)} fill="none" stroke="var(--track)" strokeWidth="10" strokeLinecap="round" />
        <path
          d={arc(c, c, r, 180, 360)}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
        />
        <text x={c} y={c - 6} className="gauge-val" textAnchor="middle" fill={color}>
          {pct(value)}
        </text>
      </svg>
      {confidence != null && (
        <div className="gauge-conf">
          confidence <b>{pct(confidence)}</b>
        </div>
      )}
    </div>
  );
}

function arc(cx, cy, r, startDeg, endDeg) {
  const s = polar(cx, cy, r, startDeg);
  const e = polar(cx, cy, r, endDeg);
  const large = endDeg - startDeg <= 180 ? 0 : 1;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
}
function polar(cx, cy, r, deg) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

export function LiveIndicator() {
  const { connected } = useLiveStatus();
  return (
    <span className={`live-ind ${connected ? "on" : "off"}`}>
      <span className="live-dot" /> {connected ? "LIVE" : "offline"}
    </span>
  );
}

export function Weight({ value }) {
  return (
    <span className="weight" title="Weight in consensus">
      <span className="weight-bar" style={{ width: `${Math.min(100, value * 200)}%` }} />
      <span className="weight-num">{pct(value)}</span>
    </span>
  );
}
