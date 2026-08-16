import React from "react";
import { cn } from "@/lib/utils";

/* Faithful recreation of the worker architecture diagram, in the site style.
   viewBox is wide; it scales to the container and scrolls on narrow screens. */

function Node({ x, y, w, h, lines, variant }) {
  const cy = y + h / 2;
  const lh = 15;
  const start = cy - ((lines.length - 1) * lh) / 2;
  const ghost = variant === "ghost";
  return (
    <g className={ghost ? "opacity-70" : undefined}>
      <rect x={x} y={y} width={w} height={h} rx="11"
        className={cn("fill-card",
          variant === "accent" ? "stroke-primary" : ghost ? "stroke-muted-foreground/60" : "stroke-border")}
        strokeWidth={variant === "accent" ? 1.6 : 1.3}
        strokeDasharray={ghost ? "5 4" : undefined} />
      {lines.map((ln, i) => (
        <text key={i} x={x + w / 2} y={start + i * lh} textAnchor="middle" dominantBaseline="middle"
          className={cn("text-[12.5px]",
            variant === "accent" ? "fill-foreground font-medium" : ghost ? "fill-muted-foreground" : "fill-foreground")}>
          {ln}
        </text>
      ))}
    </g>
  );
}

const Edge = ({ d, dashed }) => (
  <path d={d} className="fill-none stroke-foreground/40" strokeWidth="1.4"
    strokeDasharray={dashed ? "5 5" : undefined} markerEnd="url(#pd-arrow)" />
);

const Label = ({ x, y, children, serif, size = 12, muted }) => (
  <text x={x} y={y} className={cn(serif ? "font-heading" : "", muted ? "fill-muted-foreground" : "fill-foreground")}
    style={{ fontSize: size, fontWeight: serif ? 500 : 400 }}>{children}</text>
);

export default function ProcessDiagram() {
  return (
    <div className="overflow-x-auto">
      <svg viewBox="0 0 1920 1140" className="block h-auto w-full min-w-230" role="img" aria-label="Multi-agent forecast architecture diagram">
        <defs>
          <marker id="pd-arrow" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">
            <path d="M0,0 L7,3 L0,6 Z" className="fill-foreground/45" />
          </marker>
        </defs>

        {/* section labels */}
        <Label x={112} y={92} serif size={21}>Initialiser agent</Label>
        <Label x={975} y={92} serif size={21}>Signal extractor</Label>
        <Label x={112} y={726} serif size={21}>Analyst agent</Label>

        {/* ---- top tier edges ---- */}
        {/* define -> profile */}
        <Edge d="M262,333 L356,334" />
        {/* profile -> signals */}
        <Edge d="M542,318 C620,300 640,320 698,320" />
        <Edge d="M542,338 L698,383" />
        <Edge d="M542,352 C620,410 640,446 698,447" />
        {/* financial reports -> sub-agents (x5) */}
        <Edge d="M864,312 C930,270 950,224 998,220" />
        <Edge d="M864,320 L998,289" />
        <Edge d="M864,328 C930,352 950,356 998,358" />
        {/* sub-agent -> inspector */}
        <Edge d="M1152,219 L1286,219" />
        <Edge d="M1152,289 L1286,289" />
        <Edge d="M1152,359 L1286,359" />
        {/* inspectors -> reconciliation (top one rejected -> X, no edge) */}
        <Edge d="M1472,289 L1541,281" />
        <Edge d="M1472,359 C1510,340 1520,300 1541,292" />
        {/* rejected inspector -> X */}
        <path d="M1472,219 L1520,214" className="fill-none stroke-down/70" strokeWidth="1.4" />
        {/* feedback: reconciliation -> back to signal */}
        <path d="M1620,312 C1560,780 1040,800 866,336" className="fill-none stroke-foreground/40" strokeWidth="1.4" markerEnd="url(#pd-arrow)" />
        <Label x={1150} y={735} muted size={12}>Write report back to signal</Label>

        {/* ---- top tier nodes ---- */}
        <Node x={112} y={300} w={150} h={66} lines={["Define company +", "metrics to predict"]} />
        <Node x={356} y={298} w={186} h={72} lines={["Create company profile", "(deep research)"]} />
        <Label x={362} y={402} muted size={12}>— then request signals</Label>
        <Label x={612} y={286} muted size={12}>For each signal</Label>

        <Node x={698} y={296} w={166} h={46} lines={["Financial reports"]} />
        <Node x={698} y={360} w={166} h={46} lines={["Oil price forecast"]} />
        <Node x={698} y={424} w={166} h={46} lines={["…"]} />

        <Label x={905} y={244} muted size={12}>×5</Label>
        <Node x={998} y={196} w={154} h={46} lines={["Sub-agent"]} />
        <Node x={998} y={266} w={154} h={46} lines={["Sub-agent"]} />
        <Node x={998} y={336} w={154} h={46} lines={["Sub-agent"]} />

        <Node x={1286} y={196} w={186} h={46} lines={["Reasoning inspector"]} />
        <Node x={1286} y={266} w={186} h={46} lines={["Reasoning inspector"]} />
        <Node x={1286} y={336} w={186} h={46} lines={["Reasoning inspector"]} />

        {/* rejected X */}
        <g className="stroke-down" strokeWidth="3.2" strokeLinecap="round">
          <line x1="1524" y1="200" x2="1556" y2="232" />
          <line x1="1556" y1="200" x2="1524" y2="232" />
        </g>

        <Node x={1541} y={250} w={158} h={58} lines={["Reconciliation agent"]} variant="accent" />

        {/* ---- bottom tier ---- */}
        {/* signal -> middle analysis column */}
        <Edge d="M780,472 C760,620 660,700 642,754" />

        {/* analysis -> review (each column) */}
        <Edge d="M300,828 L300,846" />
        <Edge d="M642,828 L642,846" />
        <Edge d="M984,828 L984,846" />

        {/* reviews -> final */}
        <Edge d="M300,918 C360,970 500,988 560,1006" />
        <Edge d="M642,918 L648,1004" />
        <Edge d="M984,918 C924,970 800,988 742,1006" />

        {[150, 492, 834].map((x, i) => (
          <React.Fragment key={i}>
            <Node x={x} y={760} w={300} h={66} lines={["Analysis based on", "the extracted data"]} />
            <Node x={x} y={848} w={300} h={66} lines={["Review the reasoning process", "+ evidence chain"]} />
          </React.Fragment>
        ))}

        <Node x={505} y={1006} w={290} h={60} lines={["Final report based on consensus"]} variant="accent" />

        {/* ---- next steps: global-memory feedback loop (future work, dashed) ---- */}
        <Label x={40} y={986} muted size={12}>Next steps · future work</Label>
        <Node x={40} y={1000} w={160} h={56} lines={["Global memory"]} variant="ghost" />
        <Node x={228} y={1000} w={232} h={56} lines={["Evaluate quality on reporting"]} variant="ghost" />
        {/* final report -> evaluate -> global memory */}
        <Edge d="M505,1034 L466,1030" dashed />
        <Edge d="M228,1028 L204,1028" dashed />
        {/* global memory curls up the left edge, back into the initialiser */}
        <path d="M52,1000 C6,700 6,410 108,344" className="fill-none stroke-muted-foreground/55"
          strokeWidth="1.4" strokeDasharray="5 4" markerEnd="url(#pd-arrow)" />

        {/* ---- model sandbox (future work, dashed) ---- */}
        <Label x={1732} y={862} muted size={12}>Future work</Label>
        <Node x={1732} y={874} w={156} h={92}
          lines={["Model sandbox", "estimation model ↔", "historic FY23–25", "→ score"]} variant="ghost" />
        {/* consensus <-> sandbox */}
        <path d="M795,1030 C1300,1030 1500,940 1728,924" className="fill-none stroke-muted-foreground/55"
          strokeWidth="1.4" strokeDasharray="5 4" markerEnd="url(#pd-arrow)" />
      </svg>
    </div>
  );
}
