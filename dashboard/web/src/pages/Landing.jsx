import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Logo } from "../ui.jsx";
import ProcessDiagram from "../components/ProcessDiagram.jsx";
import { cn } from "@/lib/utils";

/* Reveal-on-scroll wrapper */
function Reveal({ as: Tag = "div", className = "", delay = 0, children }) {
  const ref = useRef(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setShown(true); io.disconnect(); } },
      { threshold: 0.14 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <Tag ref={ref} style={{ transitionDelay: `${delay}ms` }}
      className={cn("transition-all duration-700 ease-[cubic-bezier(.2,.7,.2,1)]",
        shown ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4", className)}>
      {children}
    </Tag>
  );
}

const WORKERS = [
  { slug: "home-depot", name: "Home Depot" },
  { slug: "analog-devices", name: "Analog Devices" },
  { slug: "hays", name: "Hays plc" },
  { slug: "deere", name: "Deere & Co." },
];

const ROLES = [
  ["anchor", "var(--primary)", "a direct starting range, e.g. management guidance"],
  ["driver", "#4f7a8a", "a quantified effect applied through a formula"],
  ["modifier", "#9a7bb0", "qualitative context — no false precision"],
  ["scenario", "#c99a3a", "a conditional risk, kept out of the base"],
];

const CHAIN = ["source + hash", "exact quotation", "typed observation", "validation", "Decimal formula", "forecast value"];

const IMPLEMENTED = [
  "Source-backed JSON profiles and signal maps",
  "Extraction resolvers over a frozen, hash-verified corpus returning value + confidence",
  "Reasoning review that drops non-evidence-grounded answers",
  "Deterministic anchor + driver combination in Decimal",
  "Replayable receipts — every value traces source → formula",
];
const EXCLUDED = [
  "Generic news sentiment",
  "Arbitrary model-generated weights",
  "Unrestricted LLM arithmetic",
  "A universal financial ontology",
];

function SecHead({ eyebrow, title, children, className }) {
  return (
    <Reveal className={cn("mx-auto mb-9 max-w-2xl text-center", className)}>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{eyebrow}</p>
      <h2 className="mt-2.5 font-heading text-[clamp(26px,3.6vw,36px)] font-medium leading-tight">{title}</h2>
      {children && <p className="mt-2.5 text-[15px] text-muted-foreground">{children}</p>}
    </Reveal>
  );
}

export default function Landing() {
  return (
    <div>
      {/* HERO */}
      <header className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(1000px_480px_at_78%_-10%,color-mix(in_oklab,var(--primary)_11%,transparent),transparent_60%)]" />
        <div className="relative mx-auto max-w-4xl px-6 pt-20 pb-10 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Agents vs Wall Street</p>
          <h1 className="mx-auto mt-4 max-w-[17ch] font-heading text-[clamp(38px,6.4vw,68px)] font-medium leading-[1.03]">
            An evidence-to-forecast <em className="italic text-primary">compiler</em>
          </h1>
          <p className="mx-auto mt-5 max-w-[58ch] text-[clamp(16px,2.2vw,19px)] leading-relaxed text-foreground/75">
            Four agents per company. An <em className="italic text-primary">initialiser</em> researches the profile and
            requests the signals; a <em className="italic text-primary">signal extractor</em> fans out sub-agents and
            discards any that answered from memory instead of evidence; an <em className="italic text-primary">analyst</em>
            reconciles the survivors into a consensus — and nothing enters a number unless it passes deterministic validation.
          </p>

          <div className="mx-auto mt-7 flex flex-wrap items-center justify-center gap-3">
            <Link to="/workspaces" className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition hover:opacity-90">
              Open the dashboard <ArrowRight className="size-4" />
            </Link>
            <a href="#process" className="inline-flex items-center gap-2 rounded-full border bg-card px-5 py-2.5 text-sm font-medium transition hover:bg-muted">
              See the process
            </a>
          </div>

          <div className="mx-auto mt-8 max-w-[720px] rounded-xl border border-l-[3px] border-l-primary bg-card p-4 text-left">
            <p className="text-[14px] leading-relaxed text-foreground/80">
              <b className="font-heading font-semibold">The rule that keeps it honest.</b> A signal moves a number only
              when its evidence and declared transformation pass deterministic validation — never from the model's
              trained knowledge, invented sources or arbitrary weights.
            </p>
          </div>
        </div>
      </header>

      {/* PROCESS */}
      <section id="process" className="border-t py-12">
        <div className="mx-auto max-w-[1080px] px-6">
          <SecHead eyebrow="How it works" title="Initialiser → signal extractor → analyst → consensus">
            One initialiser per company, run in parallel. It deep-researches a source-backed profile and requests the
            signals; the signal extractor fans out sub-agents per signal and drops any that aren't grounded; the analyst
            reviews the survivors and agrees a consensus figure.
          </SecHead>

          {/* initialiser strip */}
          <Reveal className="mb-8 flex flex-wrap items-center justify-center gap-2.5 text-sm">
            <span className="rounded-full bg-primary px-4 py-1.5 font-medium text-primary-foreground">Initialiser agent</span>
            <ArrowRight className="size-4 text-muted-foreground" />
            {WORKERS.map((w) => (
              <span key={w.slug} className="inline-flex items-center gap-2 rounded-full border bg-card py-1 pl-1 pr-3">
                <Logo slug={w.slug} name={w.name} size="sm" className="!size-6 !rounded-full !p-1" />
                <span className="text-[13px] font-medium">{w.name}</span>
              </span>
            ))}
          </Reveal>

          {/* architecture diagram */}
          <Reveal className="rounded-2xl border bg-card p-4 sm:p-6">
            <ProcessDiagram />
          </Reveal>

          {/* grounding callout */}
          <Reveal className="mt-6 rounded-xl bg-primary/5 p-4 ring-1 ring-primary/15">
            <p className="text-[13.5px] leading-relaxed text-foreground/80">
              <b className="font-heading font-medium">The evidence-grounding check.</b> For every signal, sub-agents
              web-search for the evidence (Tavily) and extract the number from the frozen, hash-verified corpus, returning a
              value with a confidence. A <em className="not-italic font-medium">reasoning inspector</em> then reads each one
              and rejects any agent that answered from trained knowledge instead of the evidence it actually read. Only
              grounded signals reach the reconciliation agent, whose report is written back to the signal.
            </p>
          </Reveal>
        </div>
      </section>

      {/* ROLES + PROVENANCE (compact) */}
      <section className="border-t py-12">
        <div className="mx-auto max-w-[1080px] px-6">
          <SecHead eyebrow="How a signal counts" title="A role, not an arbitrary weight">
            Every signal is assigned a role, and the engine combines signals by role — never by an arbitrary numeric weight.
          </SecHead>
          <Reveal className="mx-auto flex max-w-4xl flex-wrap justify-center gap-2.5">
            {ROLES.map(([tag, color, desc]) => (
              <div key={tag} className="flex items-center gap-2 rounded-full border bg-card py-1.5 pl-2.5 pr-4">
                <span className="rounded-md px-2 py-0.5 font-mono text-[11px] font-semibold"
                  style={{ color, background: `color-mix(in oklab, ${color} 12%, transparent)` }}>{tag}</span>
                <span className="text-[12.5px] text-muted-foreground">{desc}</span>
              </div>
            ))}
          </Reveal>

          <Reveal className="mt-10">
            <p className="mb-3 text-center text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Every number keeps its receipt
            </p>
            <div className="flex flex-wrap items-center justify-center gap-x-1.5 gap-y-2">
              {CHAIN.map((c, i) => (
                <React.Fragment key={c}>
                  <span className="rounded-lg border bg-card px-3 py-1.5 text-[12.5px] font-medium">{c}</span>
                  {i < CHAIN.length - 1 && <ArrowRight className="size-3.5 text-muted-foreground" />}
                </React.Fragment>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* SCOPE */}
      <section className="border-t py-12">
        <div className="mx-auto max-w-[1080px] px-6">
          <SecHead eyebrow="Disciplined scope" title="What's in, and what's deliberately out" />
          <Reveal className="mx-auto grid max-w-4xl grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-2xl border bg-card p-6">
              <h3 className="flex items-center gap-2 font-heading text-base font-medium">
                <span className="grid size-5 place-items-center rounded-md bg-up/15 text-xs font-bold text-up">✓</span>
                Built
              </h3>
              <ul className="mt-3 flex flex-col gap-2">
                {IMPLEMENTED.map((t) => (
                  <li key={t} className="flex gap-2.5 text-[13.5px] leading-snug text-foreground/80">
                    <span className="mt-0.5 text-up">✓</span>{t}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border bg-card p-6">
              <h3 className="flex items-center gap-2 font-heading text-base font-medium">
                <span className="grid size-5 place-items-center rounded-md bg-down/15 text-xs font-bold text-down">✕</span>
                Off the critical path
              </h3>
              <ul className="mt-3 flex flex-col gap-2">
                {EXCLUDED.map((t) => (
                  <li key={t} className="flex gap-2.5 text-[13.5px] leading-snug text-foreground/80">
                    <span className="mt-0.5 text-down">✕</span>{t}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="border-t py-12 text-center text-sm text-muted-foreground">
        <div className="mb-2 font-heading text-xl text-foreground">Centurion</div>
        <p>
          <Link to="/workspaces" className="font-medium text-primary hover:underline">Open the dashboard</Link>
          {"  ·  "}
          <a href="https://github.com/KiishiAD/agents-vs-wall-street-starter" className="font-medium text-primary hover:underline">Repository</a>
        </p>
      </footer>
    </div>
  );
}
