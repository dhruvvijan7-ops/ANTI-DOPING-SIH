import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  FileCheck2,
  Fingerprint,
  GitBranch,
  Layers3,
  Link2,
  ShieldCheck,
  Sparkles,
  Workflow as WorkflowIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Intro, { INTRO_ZOOM_MS, type IntroPoint } from "@/components/landing/Intro";
import { Reveal, prefersReducedMotion } from "@/components/landing/Reveal";

const NAV_LINKS = [
  { id: "problem", href: "#problem", label: "The problem" },
  { id: "how-it-works", href: "#how-it-works", label: "How it works" },
  { id: "signals", href: "#signals", label: "Signals" },
  { id: "workflow", href: "#workflow", label: "Workflow" },
  { id: "integrity", href: "#integrity", label: "Integrity" },
  { id: "faq", href: "#faq", label: "FAQ" },
];

function smoothScrollTo(hash: string) {
  const target = document.querySelector(hash);
  if (target) {
    target.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
  }
}

export default function Landing() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [focusedNav, setFocusedNav] = useState<string | null>(null);
  const [reveal, setReveal] = useState<{ zooming: boolean; origin: IntroPoint | null }>({
    zooming: false,
    origin: null,
  });

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleNavClick = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
      e.preventDefault();
      const id = href.slice(1);
      smoothScrollTo(href);
      setMenuOpen(false);
      setFocusedNav(id);
      window.history.replaceState(null, "", href);
      const navTimer = window.setTimeout(() => setFocusedNav(null), 1800);
      // best-effort cleanup on unmount
      void navTimer;
    },
    [],
  );

  return (
    <div className="min-h-screen bg-paper-50 text-ink-950">
      <Intro
        onComplete={() => {
          setMenuOpen(false);
          setReveal({ zooming: false, origin: null });
        }}
        onZoom={(dot) => setReveal({ zooming: true, origin: dot })}
      />
      <div
        className={reveal.zooming ? "will-change-transform" : undefined}
        style={
          reveal.zooming && reveal.origin
            ? {
                transformOrigin: `${reveal.origin.x}px ${reveal.origin.y}px`,
                animation: `intro-landing-reveal ${INTRO_ZOOM_MS}ms cubic-bezier(0.25, 0, 0.2, 1) forwards`,
              }
            : undefined
        }
      >
        <a
          href="#top"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-ink-950 focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-paper-50"
        >
          Skip to content
        </a>
      {/* 1. Navigation */}
      <header
        className={cn(
          "sticky top-0 z-40 border-b transition-all",
          scrolled ? "border-ink-100 bg-paper-50/95 backdrop-blur" : "border-transparent",
        )}
      >
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <a href="#top" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-ink-950 text-sm font-bold text-paper-50">V</div>
            <div className="leading-tight">
              <p className="text-sm font-semibold tracking-wide">VERITY</p>
              <p className="text-[11px] text-ink-500">Anti-Doping Intelligence & Investigations</p>
            </div>
          </a>
          <nav className="hidden items-center gap-6 text-sm font-medium text-ink-700 md:flex" aria-label="Landing sections">
            {NAV_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                data-nav={l.id}
                onClick={(e) => handleNavClick(e, l.href)}
                className={cn(
                  "transition-colors hover:text-signal-700",
                  focusedNav === l.id && "text-signal-700",
                )}
              >
                {l.label}
              </a>
            ))}
          </nav>
          <Link to="/login" className="inline-flex h-9 items-center gap-1.5 rounded-md bg-ink-950 px-4 text-sm font-medium text-paper-50 transition-colors hover:bg-ink-900">
            Sign in <ArrowRight className="h-4 w-4" />
          </Link>
          <button
            className="rounded-md p-2 text-ink-700 md:hidden"
            onClick={() => setMenuOpen((o) => !o)}
            aria-expanded={menuOpen}
            aria-label="Toggle menu"
          >
            <MenuGlyph />
          </button>
        </div>
        {menuOpen ? (
          <nav className="border-t border-ink-100 bg-paper-50 px-5 py-3 md:hidden" aria-label="Mobile sections">
            {NAV_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                data-nav={l.id}
                onClick={(e) => handleNavClick(e, l.href)}
                className={cn(
                  "block py-2 text-sm font-medium text-ink-700 hover:text-signal-700",
                  focusedNav === l.id && "text-signal-700",
                )}
              >
                {l.label}
              </a>
            ))}
          </nav>
        ) : null}
      </header>

      <main id="top">
        <Hero />
        <TrustStrip />
        <div className="reveal">
          <Problem />
        </div>
        <div className="reveal">
          <Pipeline />
        </div>
        <div className="reveal">
          <Signals />
        </div>
        <div className="reveal">
          <ExplainablePriority />
        </div>
        <div className="reveal">
          <Workflow />
        </div>
        <div className="reveal">
          <HumanInLoop />
        </div>
        <div className="reveal">
          <GroundedAi />
        </div>
        <div className="reveal">
          <EvidenceIntegrity />
        </div>
        <div className="reveal">
          <Faq />
        </div>
        <div className="reveal">
          <Cta />
        </div>
      </main>

      <Footer />
      </div>
    </div>
  );
}

/* 2. Hero */
function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <svg className="h-full w-full" viewBox="0 0 1200 640" preserveAspectRatio="xMidYMid slice">
          <defs>
            <radialGradient id="hero-glow" cx="70%" cy="30%" r="70%">
              <stop offset="0%" stopColor="#10a3a3" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#10a3a3" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect width="1200" height="640" fill="url(#hero-glow)" />
          <g className="hero-grid" stroke="#14243a" strokeOpacity="0.06">
            {Array.from({ length: 16 }).map((_, i) => (
              <line key={`v${i}`} x1={i * 80} y1={0} x2={i * 80} y2={640} />
            ))}
            {Array.from({ length: 9 }).map((_, i) => (
              <line key={`h${i}`} x1={0} y1={i * 80} x2={1200} y2={i * 80} />
            ))}
          </g>
        </svg>
      </div>

      <div className="relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-5 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:py-28">
        <div className="max-w-2xl">
          <p className="inline-flex items-center gap-2 rounded-full border border-ink-200 bg-white px-3 py-1 text-xs font-medium text-ink-700">
            <ShieldCheck className="h-3.5 w-3.5 text-signal-700" /> Built for integrity agencies
          </p>
          <h1 className="mt-5 font-serif text-4xl font-medium leading-[1.12] tracking-tight sm:text-5xl lg:text-[3.4rem]">
            Intelligence that explains <em className="not-italic text-signal-700">why</em> a concern arose — never a verdict
            about an athlete.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-ink-600 sm:text-lg">
            VERITY fuses rule-based detection, statistical anomaly detection, and relationship context into one scored,
            explainable picture — then hands investigators tools, evidence and a grounded assistant, while keeping every
            step audited.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/login" className="inline-flex h-11 items-center gap-2 rounded-md bg-ink-950 px-5 text-sm font-medium text-paper-50 transition-colors hover:bg-ink-900">
              Enter the platform <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="#how-it-works" className="inline-flex h-11 items-center rounded-md border border-ink-300 bg-white px-5 text-sm font-medium text-ink-800 transition-colors hover:border-ink-400 hover:bg-ink-50">
              See how detection works
            </a>          </div>
        </div>

        <HeroDiagram />
      </div>
    </section>
  );
}

function HeroDiagram() {
  return (
    <div className="relative mx-auto hidden max-w-md lg:block" aria-hidden>
      <svg viewBox="0 0 440 440" className="h-auto w-full">
        <defs>
          <linearGradient id="node-fill" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#14243a" />
            <stop offset="100%" stopColor="#1e3a5f" />
          </linearGradient>
        </defs>
        <circle cx="220" cy="220" r="118" fill="none" stroke="#10a3a3" strokeOpacity="0.35" strokeDasharray="4 8" strokeWidth="1.5" />
        <g stroke="#10a3a3" strokeOpacity="0.5" strokeWidth="1.2">
          <line x1="220" y1="220" x2="92" y2="118" />
          <line x1="220" y1="220" x2="356" y2="110" />
          <line x1="220" y1="220" x2="118" y2="352" />
          <line x1="220" y1="220" x2="344" y2="336" />
        </g>
        <g fontFamily="Georgia, serif">
          <circle cx="220" cy="220" r="56" fill="url(#node-fill)" />
          <text x="220" y="215" textAnchor="middle" fill="#f4f1ea" fontSize="15" fontWeight="600">Subject</text>
          <text x="220" y="235" textAnchor="middle" fill="#9fb4c8" fontSize="11">SYN-ATH-000</text>

          <g>
            <circle cx="92" cy="118" r="30" fill="#0e7490" />
            <text x="92" y="114" textAnchor="middle" fill="#fff" fontSize="10">Rule</text>
            <text x="92" y="128" textAnchor="middle" fill="#d7f0f4" fontSize="9">signals</text>
          </g>
          <g>
            <circle cx="356" cy="110" r="30" fill="#b45309" />
            <text x="356" y="106" textAnchor="middle" fill="#fff" fontSize="10">Anomaly</text>
            <text x="356" y="120" textAnchor="middle" fill="#fdeecd" fontSize="9">score</text>
          </g>
          <g>
            <circle cx="118" cy="352" r="30" fill="#065f46" />
            <text x="118" y="348" textAnchor="middle" fill="#fff" fontSize="10">Temporal</text>
            <text x="118" y="362" textAnchor="middle" fill="#d7f0e4" fontSize="9">correlation</text>
          </g>
          <g>
            <circle cx="344" cy="336" r="30" fill="#7c2d12" />
            <text x="344" y="332" textAnchor="middle" fill="#fff" fontSize="10">Network</text>
            <text x="344" y="346" textAnchor="middle" fill="#fde6d8" fontSize="9">context</text>
          </g>
        </g>
        <circle cx="220" cy="220" r="62" fill="none" stroke="#10a3a3" strokeWidth="2" strokeDasharray="1 7" strokeLinecap="round" />
      </svg>
      <div className="absolute -bottom-2 left-1/2 w-64 -translate-x-1/2 rounded-lg border border-ink-100 bg-white px-3 py-2 text-center shadow-lift">
        <p className="text-xs text-ink-600">Composite priority 86/100</p>
        <p className="text-[11px] text-ink-500">Explainable · scored · audited</p>
      </div>
    </div>
  );
}

/* 3. Trust / principles strip */
function TrustStrip() {
  const items = [
    { icon: <ShieldCheck className="h-4 w-4" />, title: "Crucial distinction", body: "An anomaly is a lead, not a statement about anyone. Priority scores rank lead strength — never a judgement about guilt or innocence." },
    { icon: <FileCheck2 className="h-4 w-4" />, title: "Every step audited", body: "Analysis, triage, assignment, findings — a tamper-evident audit record is kept for each case." },
    { icon: <Fingerprint className="h-4 w-4" />, title: "Grounded, not speculative", body: "The assistant answers only from case records and labels each statement with its basis." },
  ];
  return (
    <section className="border-y border-ink-100 bg-white">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 px-5 py-10 sm:grid-cols-3">
        {items.map((i) => (
          <div key={i.title} className="flex gap-3">
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-signal-50 text-signal-700">{i.icon}</div>
            <div>
              <p className="text-sm font-semibold text-ink-950">{i.title}</p>
              <p className="mt-1 text-sm leading-relaxed text-ink-600">{i.body}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* 4. Problem */
function Problem() {
  return (
    <Section id="problem" kicker="The problem" title={<>Doping indicators hide inside the noise of routine data.</>}>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-4 text-ink-700">
          <p>
            Testing programmes generate thousands of records each season — biological passports, test results, whereabouts
            statements, travel logs, competition histories and field intelligence. Individually, each record looks routine.
          </p>
          <p>
            The concern only becomes visible when patterns line up: an unusual blood profile alongside missed whereabouts, a
            cluster of related support-person links, a spike in low-severity rule flags on the same network.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <ProblemCard stat="Single signals" text="Rarely conclusive on their own, easy to miss in a daily workload." />
          <ProblemCard stat="Manual review" text="Serial review of isolated records overlooks cross-source context." />
          <ProblemCard stat="Explainability" text="Automation that cannot justify its output is unusable in due-process contexts." />
        </div>
      </div>
    </Section>
  );
}

function ProblemCard({ stat, text }: { stat: string; text: string }) {
  return (
    <div className="rounded-lg border border-ink-100 bg-white p-4">
      <p className="text-sm font-semibold text-signal-700">{stat}</p>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{text}</p>
    </div>
  );
}

/* 5. Pipeline */
function Pipeline() {
  const steps = [
    { n: "01", icon: <WorkflowIcon className="h-5 w-5" />, title: "Ingestion", body: "Tests, ABP readings, whereabouts, travel, events and field intelligence are normalised into one profile per subject." },
    { n: "02", icon: <Layers3 className="h-5 w-5" />, title: "Feature engineering", body: "Fixed-version feature sets are computed per subject so the platform produces reproducible results." },
    { n: "03", icon: <BrainCircuit className="h-5 w-5" />, title: "Multi-signal scoring", body: "Rules, isolation-forest anomaly scoring, correlations and network context are combined into a weighted composite." },
    { n: "04", icon: <Sparkles className="h-5 w-5" />, title: "Alerts with reasons", body: "Empty alerts never reach investigators. Each alert carries the exact signals and weights behind its score." },
    { n: "05", icon: <GitBranch className="h-5 w-5" />, title: "Investigation workspace", body: "Timeline, evidence with integrity hashes, findings, tasks, reports and a grounded assistant — all in one place." },
  ];
  return (
    <Section id="how-it-works" kicker="How it works" title={<>From raw records to a defensible case file.</>} tone="dark">
      <ol className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
        {steps.map((s) => (
          <li key={s.n} className="rounded-lg border border-ink-800 bg-ink-900 p-4">
            <div className="flex items-center justify-between">
              <span className="font-serif text-2xl text-signal-400">{s.n}</span>
              <span className="text-signal-300">{s.icon}</span>
            </div>
            <p className="mt-3 text-sm font-semibold text-paper-50">{s.title}</p>
            <p className="mt-1.5 text-xs leading-relaxed text-ink-400">{s.body}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}

/* 6. Signals */
function Signals() {
  const signals = [
    { title: "Rule-based signals", desc: "Deterministic conditions aligned to the analytical model — each firing is logged with its expression and weight.", tone: "text-ink-900" },
    { title: "Anomaly detection", desc: "An isolation-forest model marks profiles that deviate from the cohort, with per-feature contribution breakdowns.", tone: "text-ink-900" },
    { title: "Temporal correlations", desc: "Signals that cluster within a moving window surface patterns that serial review would miss.", tone: "text-ink-900" },
    { title: "Network context", desc: "The subject’s position among support persons, teams and connected high-priority profiles informs the composite.", tone: "text-ink-900" },
  ];
  return (
    <Section id="signals" kicker="Multi-signal synthesis" title={<>Five lenses, one explainable composite.</>}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {signals.map((s) => (
          <div key={s.title} className="rounded-lg border border-ink-100 bg-white p-5">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-signal-600" />
              <p className="text-sm font-semibold text-ink-950">{s.title}</p>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">{s.desc}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* 7. Explainable priority */
function ExplainablePriority() {
  const rows = [
    { name: "Rule-based signals", value: 0.82, weight: "35%" },
    { name: "Anomaly detection", value: 0.74, weight: "25%" },
    { name: "Correlations", value: 0.6, weight: "15%" },
    { name: "Temporal patterns", value: 0.66, weight: "10%" },
    { name: "Network position", value: 0.7, weight: "10%" },
    { name: "Source quality", value: 0.55, weight: "5%" },
  ];
  return (
    <Section id="priority" kicker="Explainable priority" title={<>A score you can open up and audit.</>}>
      <div className="grid grid-cols-1 items-start gap-10 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-4 text-ink-700">
          <p>
            Every alert exposes its own arithmetic: the composite score, the contributing signal scores, and the weights
            chosen for the model. Investigators can trace a score back to the exact rule firings, anomaly contributions and
            relationship counts that produced it.
          </p>
          <p>
            That same breakdown is stored in the case file — so the reasoning an investigator relied on remains available
            long after the alert has been converted.
          </p>
        </div>
        <div className="rounded-lg border border-ink-100 bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm font-medium text-ink-900">Alert CAL-2026-0041 — component scores</p>
            <p className="font-serif text-2xl text-signal-700">86</p>
          </div>
          <div className="space-y-3">
            {rows.map((r) => (
              <div key={r.name}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-ink-700">{r.name}</span>
                  <span className="tabular-nums text-ink-500">{Math.round(r.value * 100)} · weight {r.weight}</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
                  <div className="h-full rounded-full bg-signal-600" style={{ width: `${Math.round(r.value * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Section>
  );
}

/* 8. Workflow */
function Workflow() {
  const stages = [
    { title: "Triage", text: "Review, dismiss, escalate or convert an alert — every decision is attributed." },
    { title: "Investigate", text: "Build the timeline, log evidence, write findings and run tasks in one workspace." },
    { title: "Decide", text: "Link supporting and contradicting evidence to each finding before anything moves forward." },
    { title: "Report", text: "Publish versions that capture the full case record at a point in time." },
  ];
  return (
    <Section id="workflow" kicker="Investigator workflow" title={<>One workspace from first lead to final record.</>}>
      <ol className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stages.map((s, i) => (
          <li key={s.title} className="relative rounded-lg border border-ink-100 bg-white p-5">
            <span className="font-serif text-3xl text-ink-200">{String(i + 1).padStart(2, "0")}</span>
            <p className="mt-2 text-sm font-semibold text-ink-950">{s.title}</p>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{s.text}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}

/* 9. Human in the loop */
function HumanInLoop() {
  return (
    <Section id="humans" kicker="Human in the loop" title={<>The assessor holds the decision. The platform keeps the receipts.</>} tone="paper">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <HumanCard n="1" title="Every alert is optional" text="Nothing is auto-escalated. A scored alert enters the queue for a human to triage on its merits." />
        <HumanCard n="2" title="Findings need defence" text="A finding must state its evidence and confidence stage. Contradicting evidence lives beside supporting evidence." />
        <HumanCard n="3" title="Nothing is scrubbed" text="Assessments, assignment notes, report versions and changes to evidence are all preserved in the audit trail." />
      </div>
    </Section>
  );
}

function HumanCard({ n, title, text }: { n: string; title: string; text: string }) {
  return (
    <div className="rounded-lg border border-ink-100 bg-white p-6">
      <p className="font-serif text-3xl text-signal-700">{n}</p>
      <p className="mt-2 text-sm font-semibold text-ink-950">{title}</p>
      <p className="mt-2 text-sm leading-relaxed text-ink-600">{text}</p>
    </div>
  );
}

/* 10. Grounded AI */
function GroundedAi() {
  return (
    <Section id="ai" kicker="Grounded AI" title={<>Assistance that cites its own case file.</>}>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4 text-ink-700">
          <p>
            The assistant composes summaries, flags information gaps, suggests questions and drafts report sections — all
            deterministically from the case records. Every response carries a disclaimer and labels each statement with the
            kind of claim it is.
          </p>
          <ul className="space-y-2 text-sm">
            {["Deterministic fallback service — no external model, no data leaves the platform", "Responses reference only the current case file", "Draft report sections map directly to the published report schema", "Suggested open questions appear, never implied conclusions"].map((t) => (
              <li key={t} className="flex items-start gap-2.5">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-signal-600" />
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-ink-100 bg-white p-5 font-mono text-xs leading-relaxed">
          <p className="mb-2 font-sans text-xs font-semibold uppercase tracking-wide text-ink-400">Example response</p>
          <p className="text-ink-800">Grounded: true</p>
          <p className="mt-2 text-ink-600">“Three test observations in the ABP window exceed two standard deviations. This is an investigative lead; it does not establish that a violation occurred.”</p>
          <p className="mt-2 text-ink-400">claim_type: analytical_observation · grounded</p>
        </div>
      </div>
    </Section>
  );
}

/* 11. Evidence integrity */
function EvidenceIntegrity() {
  const items = [
    { icon: <Fingerprint className="h-5 w-5" />, title: "Canonical hashes", text: "Each evidence item is stored with an integrity hash over a canonical form of its content." },
    { icon: <Layers3 className="h-5 w-5" />, title: "Versioned changes", text: "Every edit creates a version with author, timestamp and change reason. Nothing is silently overwritten." },
    { icon: <Link2 className="h-5 w-5" />, title: "Traceable lineage", text: "Alerts carry a traceable chain so a case can be walked back to its originating signals." },
    { icon: <ShieldCheck className="h-5 w-5" />, title: "Restricted handling", text: "Sensitivity labels control what is readable in detail views, with access decisions logged." },
  ];
  return (
    <Section id="integrity" kicker="Evidence integrity" title={<>A case file built to withstand scrutiny.</>} tone="dark">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {items.map((i) => (
          <div key={i.title} className="flex gap-3 rounded-lg border border-ink-800 bg-ink-900 p-5">
            <span className="text-signal-300">{i.icon}</span>
            <div>
              <p className="text-sm font-semibold text-paper-50">{i.title}</p>
              <p className="mt-1 text-sm leading-relaxed text-ink-400">{i.text}</p>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* 12. FAQ */
function Faq() {
  const faqs: Array<[string, string]> = [
    ["Is an alert the same as a sanction outcome?", "No. An alert is a scored investigative lead produced from data patterns. A finding and any resulting decision require human assessment of supporting and contradicting evidence."],
    ["Can the assistant conclude anything on its own?", "No. It only describes what the case file contains and flags what is missing. The disclaimer is fixed and the claims are labelled."],
    ["What happens when evidence is changed?", "A new version is created with the author, timestamp and change reason. The prior version and its hash remain part of the record."],
    ["Which signals feed the composite score?", "Rule firings, anomaly scores, temporal and cross-source correlations, and network context, combined with explicitly documented weights."],
  ];
  return (
    <Section id="faq" kicker="FAQ" title={<>Straight answers.</>}>
      <div className="mx-auto max-w-3xl space-y-3">
        {faqs.map(([q, a]) => (
          <details key={q} className="group rounded-lg border border-ink-100 bg-white p-5">
            <summary className="flex cursor-pointer items-center justify-between gap-3 text-sm font-semibold text-ink-950 marker:content-none">
              {q}
              <span className="text-ink-400 transition-transform group-open:rotate-45">+</span>
            </summary>
            <p className="mt-3 text-sm leading-relaxed text-ink-600">{a}</p>
          </details>
        ))}
      </div>
    </Section>
  );
}

/* CTA */
function Cta() {
  return (
    <section id="cta" className="border-t border-ink-100 bg-signal-900">
      <div className="mx-auto max-w-6xl px-5 py-16 text-center">
        <p className="text-xs font-medium uppercase tracking-widest text-signal-300">Authorised personnel</p>
        <h2 className="mx-auto mt-3 max-w-2xl font-serif text-3xl font-medium text-paper-50 sm:text-4xl">
          The platform is live for the platform team.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-signal-100">
          Sign in with your organisational account to open the alert queue, intelligence feed and investigation workspaces.
        </p>
        <Link to="/login" className="mt-7 inline-flex h-11 items-center gap-2 rounded-md bg-paper-50 px-6 text-sm font-semibold text-ink-950 transition-colors hover:bg-white">
          Sign in to VERITY <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
}

/* 13. Footer */
function Footer() {
  return (
    <footer className="border-t border-ink-100 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 sm:flex-row">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-ink-950 text-[10px] font-bold text-paper-50">V</div>
          <p className="text-sm font-semibold text-ink-900">VERITY</p>
          <p className="text-xs text-ink-500">Anti-Doping Intelligence & Investigations</p>
        </div>
        <p className="text-xs text-ink-400">
          Operational intelligence platform for anti-doping analytical teams. Access is restricted to authorised users.
        </p>
      </div>
    </footer>
  );
}

/* Shared section layout */
function Section({
  id,
  kicker,
  title,
  tone = "paper",
  children,
}: {
  id: string;
  kicker: string;
  title: ReactNode;
  tone?: "paper" | "dark";
  children: ReactNode;
}) {
  return (
    <section id={id} className={cn("relative scroll-mt-20 border-b border-ink-100", tone === "dark" ? "bg-ink-950" : "bg-paper-50")}>
      <span id={`${id}-anchor`} className="absolute -top-16 scroll-mt-20" aria-hidden />
      <div className="mx-auto max-w-6xl px-5 py-16 lg:py-20">
        <Reveal>
          <p className={cn("text-xs font-medium uppercase tracking-widest", tone === "dark" ? "text-signal-300" : "text-signal-700")}>{kicker}</p>
          <h2
            className={cn(
              "mt-3 max-w-2xl font-serif text-3xl font-medium leading-tight tracking-tight sm:text-4xl",
              tone === "dark" ? "text-paper-50" : "text-ink-950",
            )}
          >
            {title}
          </h2>
        </Reveal>
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}

function MenuGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}