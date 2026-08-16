import React, { useState } from "react";
import { Check, X, ChevronRight, Quote, FileText, Hash, ShieldCheck, Sigma } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const ROLE = {
  anchor: { label: "anchor", color: "var(--primary)" },
  driver: { label: "driver", color: "#4f7a8a" },
  modifier: { label: "modifier", color: "#9a7bb0" },
  scenario_trigger: { label: "scenario", color: "#c99a3a" },
  constraint: { label: "constraint", color: "#6b7280" },
};

const num = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : v;
};
const mid = (r) => (r ? (Number(r.low) + Number(r.high)) / 2 : 0);

function contribution(role, obs, units) {
  if (role === "anchor") return `Sets the base range → midpoint ${num(mid(obs.value))} ${units}`;
  if (role === "driver") {
    const v = Number(obs.value);
    return `${v >= 0 ? "+" : "−"}${num(Math.abs(v))} ${units} applied to the base`;
  }
  if (role === "modifier") return "Range context only — carries no numerical weight";
  if (role === "scenario_trigger") return "Conditional scenario — excluded from the base unless triggered";
  return "Checked after calculation";
}

function Term({ label, big, sub, faded }) {
  return (
    <div className={cn("flex min-w-30 flex-col rounded-xl border bg-card px-4 py-3", faded && "opacity-60")}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="mt-0.5 font-mono text-lg font-bold tracking-tight">{big}</span>
      {sub && <span className="text-[11px] text-muted-foreground">{sub}</span>}
    </div>
  );
}
const Op = ({ children }) => <span className="font-mono text-lg text-muted-foreground">{children}</span>;

function ProvenanceStep({ icon: Icon, label, children }) {
  return (
    <div className="relative flex gap-3 pb-3 last:pb-0">
      <div className="grid size-7 flex-none place-items-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-3.5" />
      </div>
      <div className="min-w-0">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</div>
        <div className="mt-0.5 text-[13px] leading-relaxed text-foreground/85">{children}</div>
      </div>
    </div>
  );
}

function DecisionRow({ decision, signal, source }) {
  const [open, setOpen] = useState(false);
  const obs = decision.observation || {};
  const role = obs.role || signal?.role || "modifier";
  const r = ROLE[role] || ROLE.modifier;
  const accepted = decision.accepted;
  const prov = obs.provenance || {};
  const valueText =
    obs.value && typeof obs.value === "object"
      ? `${num(obs.value.low)}–${num(obs.value.high)} ${obs.units || ""}`
      : obs.value != null
      ? `${num(obs.value)} ${obs.units || ""}`
      : "qualitative";

  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-muted/40">
        <span className="grid size-6 flex-none place-items-center rounded-full"
          style={{ background: accepted ? "color-mix(in oklab, var(--up) 15%, transparent)" : "color-mix(in oklab, var(--down) 15%, transparent)" }}>
          {accepted ? <Check className="size-3.5 text-up" /> : <X className="size-3.5 text-down" />}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium">{signal?.signal || obs.signalId}</span>
            <span className="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold"
              style={{ color: r.color, background: `color-mix(in oklab, ${r.color} 12%, transparent)` }}>{r.label}</span>
          </div>
          <div className="mt-0.5 truncate text-xs text-muted-foreground">
            {accepted ? decision.explanation : <span className="text-down">{decision.reasonCode} · {decision.explanation}</span>}
          </div>
        </div>
        <span className="hidden font-mono text-xs text-muted-foreground sm:block">{valueText}</span>
        <ChevronRight className={cn("size-4 flex-none text-muted-foreground transition-transform", open && "rotate-90")} />
      </button>

      {open && (
        <div className="border-t bg-muted/20 px-4 py-4 pl-5">
          <ProvenanceStep icon={FileText} label="Source">
            {source ? (
              <a href={source.url} target="_blank" rel="noreferrer" className="font-medium hover:underline">{source.title}</a>
            ) : prov.sourceId}
            <span className="text-muted-foreground"> — {prov.publisher}{prov.publishedAt && `, ${prov.publishedAt}`}</span>
            {prov.sourceSha256 && (
              <span className="ml-2 inline-flex items-center gap-1 font-mono text-[11px] text-muted-foreground">
                <Hash className="size-3" />{prov.sourceSha256.slice(0, 10)}…
              </span>
            )}
          </ProvenanceStep>
          {prov.exactQuote && (
            <ProvenanceStep icon={Quote} label="Exact quotation">
              <span className="italic">“{prov.exactQuote}”</span>
              {prov.locator && <span className="block text-[11px] text-muted-foreground">— {prov.locator}</span>}
            </ProvenanceStep>
          )}
          <ProvenanceStep icon={Sigma} label="Observation">
            <span className="font-mono">{valueText}</span> · {obs.period}
            {obs.evidenceQuality && <> · evidence <b className="font-medium">{obs.evidenceQuality}</b></>}
            {obs.calculation && <span className="block text-[11px] text-muted-foreground">{obs.calculation}</span>}
          </ProvenanceStep>
          <ProvenanceStep icon={ShieldCheck} label="Validation">
            {accepted
              ? <span className="text-up">accepted — passed provenance &amp; signal checks</span>
              : <span className="text-down">rejected — {decision.reasonCode}</span>}
          </ProvenanceStep>
          <ProvenanceStep icon={ChevronRight} label="Contribution">
            {contribution(role, obs, obs.units)}
          </ProvenanceStep>
        </div>
      )}
    </div>
  );
}

export default function DecisionTrail({ trace }) {
  if (!trace) return null;
  const f = trace.forecast || {};
  const units = f.units || trace.metric?.units || "";
  const sigMap = Object.fromEntries((trace.signalMap || []).map((s) => [s.signalId, s]));
  const srcMap = Object.fromEntries((trace.sources || []).map((s) => [s.id, s]));
  const decisions = [...(trace.decisions?.accepted || []), ...(trace.decisions?.rejected || [])];
  const driver = Number(f.driverAdjustment || 0);
  const anchorMid = mid(f.anchorRange);
  const issues = trace.challenge?.issues || [];

  return (
    <Card className="gap-0 p-0">
      <div className="flex flex-col gap-1 border-b p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-heading text-lg font-medium">Decision trail — {trace.metric?.name}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {trace.metric?.targetPeriod} · every value traces from a hashed source to the formula ·
            <span className={cn("ml-1 font-medium", trace.challenge?.passed ? "text-up" : "text-down")}>
              challenge {trace.challenge?.passed ? "passed" : "failed"}
            </span>
          </p>
        </div>
        <span className="font-mono text-2xl font-bold tracking-tight text-primary">
          {num(f.baseForecast)} <span className="text-sm font-medium text-muted-foreground">{units}</span>
        </span>
      </div>

      <div className="p-5">
        {/* number build-up */}
        <div className="flex flex-wrap items-center gap-3">
          <Term label="Anchor" big={num(anchorMid)} sub={`range ${num(f.anchorRange?.low)}–${num(f.anchorRange?.high)}`} />
          <Op>+</Op>
          <Term label="Drivers" big={driver === 0 ? "0" : `${driver > 0 ? "+" : "−"}${num(Math.abs(driver))}`}
            sub={driver === 0 ? "no approved drivers" : "approved adjustments"} faded={driver === 0} />
          <Op>=</Op>
          <Term label="Base forecast" big={`${num(f.baseForecast)}`} sub={units} />
          {(f.scenarios || []).length > 0 && (
            <>
              <Op>±</Op>
              <Term label="Scenarios" big={`${f.scenarios.length}`} sub="conditional" faded />
            </>
          )}
        </div>
        <div className="mt-3 rounded-lg bg-muted/40 px-3 py-2 font-mono text-[12.5px] text-foreground/70">{f.formula}</div>

        {/* decisions */}
        <div className="mt-5 mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          {decisions.length} decisions · click to trace the evidence
        </div>
        <div className="flex flex-col gap-2.5">
          {decisions.map((d, i) => (
            <DecisionRow key={i} decision={d} signal={sigMap[d.observation?.signalId]} source={srcMap[d.observation?.provenance?.sourceId]} />
          ))}
        </div>

        {/* challenge issues */}
        {issues.length > 0 && (
          <div className="mt-5 rounded-xl border border-dashed p-4">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Challenger notes</div>
            <ul className="flex flex-col gap-1.5">
              {issues.map((iss, i) => (
                <li key={i} className="flex items-start gap-2 text-[13px]">
                  <span className={cn("mt-0.5 rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold",
                    iss.severity === "error" ? "bg-down/12 text-down" : "bg-warn/15 text-warn")}>{iss.severity}</span>
                  <span className="text-foreground/80"><span className="font-mono text-xs text-muted-foreground">{iss.code}</span> — {iss.message}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  );
}
