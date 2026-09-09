import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, GitBranch, Layers, Zap } from "lucide-react";
import { useAlertDetailQuery } from "@/lib/api/queries";
import type { AlertDetail as AlertDetailType, AlertSignal, RuleResult, AnomalyResult, CorrelationResult, NetworkResult } from "@/lib/api/types";
import { ALERT_STATUS_META, priorityLabel, SIGNAL_TYPE_LABELS, SIGNAL_TYPE_ORDER } from "@/lib/constants";
import { cn, formatScore } from "@/lib/utils";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { ProgressBar } from "@/components/ui/progress";
import { TriagePanel } from "@/features/alerts/TriagePanel";

export default function AlertDetail() {
  const { alertId } = useParams();
  const [searchParams] = useSearchParams();
  const [redirecting, setRedirecting] = useState(false);

  const { data, isLoading, isError, refetch } = useAlertDetailQuery(alertId);

  if (isLoading) return <PageLoading label="Loading alert" />;
  if (isError || !data) return <ErrorState title="Could not load this alert" message="The alert may have been removed or access is restricted." onRetry={() => void refetch()} />;

  return (
    <div>
      <Link
        to={searchParams.get("back") ?? "/alerts"}
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink-600 hover:text-ink-900"
      >
        <ArrowLeft className="h-4 w-4" /> Back to alert queue
      </Link>

      <PageHeader
        eyebrow={`${data.alert.alert_ref} · detection output`}
        title={data.alert.title}
        description={
          <>
            This alert is a <strong>potential concern</strong> produced by combining multiple scored signals. It is not a
            finding and implies no conclusion about the subject.
          </>
        }
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[350px_minmax(0,1fr)]">
        <div className="space-y-6">
          <AlertSummaryCard data={data} />
          <TriagePanel
            alert={data.alert}
            onConverted={(id) => {
              setRedirecting(true);
              window.setTimeout(() => {
                window.location.href = `/investigations/${id}`;
              }, 250);
            }}
          />
          {redirecting ? <p className="text-sm text-ink-500">Opening the new case…</p> : null}
        </div>

        <div className="min-w-0 space-y-6">
          <WhyFlagged data={data} />
          <SignalsSection data={data} />
          <FeaturesSection data={data} />
          <TraceableChain data={data} />
        </div>
      </div>
    </div>
  );
}

function AlertSummaryCard({ data }: { data: AlertDetailType }) {
  const meta = ALERT_STATUS_META[data.alert.status];
  return (
    <Card>
      <CardBody className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-ink-500">Priority level</p>
            <p className="text-lg font-semibold text-ink-950">{priorityLabel(data.alert.priority_level)}</p>
          </div>
          <ScoreRingNew value={data.alert.score} />
        </div>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-ink-500">Status</dt>
            <dd><Badge tone={meta?.badge.includes("emerald") ? "success" : meta?.badge.includes("red") ? "danger" : meta?.badge.includes("amber") ? "warn" : "neutral"} className={meta?.badge}>{meta?.label ?? data.alert.status}</Badge></dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-ink-500">Analysis run</dt>
            <dd className="text-ink-800">{data.alert.analysis_run_id.slice(0, 8)}…</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-ink-500">Generated</dt>
            <dd className="text-ink-800">{data.alert.created_at}</dd>
          </div>
        </dl>
      </CardBody>
    </Card>
  );
}

function ScoreRingNew({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  const size = 72;
  const stroke = 5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = pct >= 85 ? "#dc2626" : pct >= 70 ? "#d97706" : pct >= 50 ? "#0284c7" : "#94a3b8";
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }} role="img" aria-label={`Score ${pct.toFixed(1)} out of 100`}>
      <svg width={size} height={size} aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * c} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className="absolute text-base font-semibold tabular-nums text-ink-900">{pct.toFixed(0)}</span>
    </div>
  );
}

function WhyFlagged({ data }: { data: AlertDetailType }) {
  const p = data.priority;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-amber-500" /> Why this was flagged
        </CardTitle>
      </CardHeader>
      <CardBody className="space-y-5">
        <p className="rounded-md border border-ink-100 bg-ink-50/70 p-3 text-sm leading-relaxed text-ink-800">{p.explanation}</p>
        <div className="space-y-3">
          <ComponentRow label="Rule-based signals" value={p.rule_score} weight={p.components.weights.rule} />
          <ComponentRow label="Anomaly detection" value={p.anomaly_score} weight={p.components.weights.anomaly} />
          <ComponentRow label="Correlations" value={p.correlation_score} weight={p.components.weights.correlation} />
          <ComponentRow label="Temporal patterns" value={p.temporal_score} weight={p.components.weights.temporal} />
          <ComponentRow label="Network position" value={p.network_score} weight={p.components.weights.network} />
          <ComponentRow label="Source quality" value={p.source_quality_score} weight={p.components.weights.source_quality} />
        </div>
      </CardBody>
    </Card>
  );
}

function ComponentRow({ label, value, weight }: { label: string; value: number; weight: number }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-ink-700">{label}</span>
        <span className="tabular-nums text-ink-500">
          {formatScore(value)} · weight {(weight * 100).toFixed(0)}%
        </span>
      </div>
      <ProgressBar value={value} />
    </div>
  );
}

function SignalsSection({ data }: { data: AlertDetailType }) {
  const sorted = [...data.signals].sort(
    (a, b) => SIGNAL_TYPE_ORDER.indexOf(String(a.signal_type)) - SIGNAL_TYPE_ORDER.indexOf(String(b.signal_type)),
  );
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Layers className="h-4 w-4 text-signal-600" /> Signals that contributed</CardTitle>
      </CardHeader>
      <CardBody>
        {sorted.length === 0 ? (
          <EmptyState title="No signals recorded" className="py-8" />
        ) : (
          <ul className="space-y-3">
            {sorted.map((signal) => (
              <li key={signal.id} className="rounded-md border border-ink-100 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-ink-900">{SIGNAL_TYPE_LABELS[String(signal.signal_type)] ?? String(signal.signal_type)}</p>
                  <Badge tone={signal.contributed ? "info" : "neutral"} className={signal.contributed ? "bg-signal-50 text-signal-800 ring-signal-200" : undefined}>
                    {signal.contributed ? "Contributed" : "Context only"}
                  </Badge>
                </div>
                <SignalResult signal={signal} />
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

function SignalResult({ signal }: { signal: AlertSignal }) {
  const r = signal.result as RuleResult | AnomalyResult | CorrelationResult | NetworkResult;

  if (signal.signal_type === "RULE") {
    const rule = r as RuleResult;
    return (
      <div className="mt-2 space-y-1 text-xs text-ink-600">
        <p>
          <span className="font-medium text-ink-800">{rule.name}</span> · severity {rule.severity} · weight {rule.weight}
        </p>
        <p className="font-mono text-[11px] text-ink-500">{rule.expression}</p>
        <p className={cn("font-medium", rule.triggered ? "text-amber-700" : "text-ink-500")}>
          {rule.triggered ? "Condition satisfied" : "Condition not satisfied (context)"}
        </p>
        {Object.keys(rule.detail ?? {}).length > 0 ? (
          <pre className="mt-1 overflow-x-auto rounded bg-ink-50 p-2 font-mono text-[10px] text-ink-600">
            {JSON.stringify(rule.detail, null, 2)}
          </pre>
        ) : null}
      </div>
    );
  }

  if (signal.signal_type === "ANOMALY") {
    const a = r as AnomalyResult;
    return (
      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-ink-600">
        <p><span className="text-ink-400">Normalised score</span> — {formatScore(a.normalized_score)}</p>
        <p><span className="text-ink-400">Model</span> — {a.model_version}</p>
        <p className={a.is_anomaly ? "font-medium text-amber-700" : "text-ink-500"}>
          {a.is_anomaly ? "Flagged as anomalous" : "Within expected range"}
        </p>
      </div>
    );
  }

  if (signal.signal_type === "TEMPORAL" || signal.signal_type === "CROSS_SOURCE") {
    const c = r as CorrelationResult;
    return (
      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-ink-600">
        <p><span className="text-ink-400">Score</span> — {formatScore(c.score)}</p>
        <p><span className="text-ink-400">Window</span> — {c.window_days} days</p>
        <p><span className="text-ink-400">Signals</span> — {c.signal_count} ({c.category_count} categories)</p>
        <p>{c.description}</p>
      </div>
    );
  }

  const n = r as NetworkResult;
  return (
    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-ink-600">
      <p><span className="text-ink-400">Degree</span> — {n.degree}</p>
      <p><span className="text-ink-400">Weighted degree</span> — {n.weighted_degree.toFixed ? n.weighted_degree.toFixed(1) : n.weighted_degree}</p>
      <p><span className="text-ink-400">Diversity</span> — {formatScore(n.relationship_diversity)}</p>
      <p><span className="text-ink-400">Connected high-priority</span> — {n.connected_priority_count}</p>
      {n.detail?.neighbors?.length ? <p className="col-span-2">Linked to: {n.detail.neighbors.join(", ")}</p> : null}
    </div>
  );
}

function FeaturesSection({ data }: { data: AlertDetailType }) {
  const rows = data.features ?? [];
  return (
    <Card>
      <CardHeader><CardTitle>Features used by the model</CardTitle></CardHeader>
      <CardBody>
        {rows.length === 0 ? <EmptyState title="No features returned" className="py-8" /> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-500">
                <th className="py-1.5 pr-3">Feature</th>
                <th className="py-1.5 pr-3">Version</th>
                <th className="py-1.5">Value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-50">
              {rows.slice(0, 40).map((f) => (
                <tr key={f.feature_id}>
                  <td className="py-1.5 pr-3 font-mono text-xs text-ink-800">{f.feature_id}</td>
                  <td className="py-1.5 pr-3 text-xs text-ink-500">{f.feature_version}</td>
                  <td className="py-1.5 tabular-nums text-ink-800">{formatScore(f.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardBody>
    </Card>
  );
}

function TraceableChain({ data }: { data: AlertDetailType }) {
  const chain = data.traceable_chain ?? [];
  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2"><GitBranch className="h-4 w-4 text-ink-500" /> Traceable chain</CardTitle></CardHeader>
      <CardBody>
        {chain.length === 0 ? <EmptyState title="No chain recorded" className="py-8" /> : (
          <ol className="relative border-l border-ink-100 pl-5">
            {chain.map((step, i) => (
              <li key={`${step}-${i}`} className="relative pb-4 last:pb-0">
                <span className="absolute -left-[27px] top-1 h-2.5 w-2.5 rounded-full border-2 border-white bg-signal-600" aria-hidden />
                <p className="text-sm text-ink-800">{step}</p>
              </li>
            ))}
          </ol>
        )}
      </CardBody>
    </Card>
  );
}