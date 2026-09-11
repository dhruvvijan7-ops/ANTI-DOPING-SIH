import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useCan } from "@/stores/auth";
import { useInvestigationOverviewQuery } from "@/lib/api/queries";
import { priorityLabel } from "@/lib/constants";
import { Tabs, type TabItem } from "@/components/ui/tabs";
import { PageLoading } from "@/components/ui/spinner";
import { ErrorState } from "@/components/ui/states";
import { InvOverview } from "@/features/investigation/InvOverview";
import { InvTimeline } from "@/features/investigation/InvTimeline";
import { InvEvidence } from "@/features/investigation/InvEvidence";
import { InvFindings } from "@/features/investigation/InvFindings";
import { InvTasks } from "@/features/investigation/InvTasks";
import { InvNotes } from "@/features/investigation/InvNotes";
import { InvReports } from "@/features/investigation/InvReports";
import { InvAi } from "@/features/investigation/InvAi";
import { InvAudit } from "@/features/investigation/InvAudit";
import { InvRelationships } from "@/features/investigation/InvRelationships";
import { InvIntelligence } from "@/features/investigation/InvIntelligence";

type TabKey =
  | "overview"
  | "timeline"
  | "evidence"
  | "findings"
  | "tasks"
  | "notes"
  | "relationships"
  | "intelligence"
  | "ai"
  | "reports"
  | "audit";

export default function InvestigationWorkspace() {
  const { investigationId } = useParams();
  const [tab, setTab] = useState<TabKey>("overview");

  const overview = useInvestigationOverviewQuery(investigationId);
  const canAudit = useCan("audit:read");

  if (overview.isLoading) return <PageLoading label="Loading case workspace" />;
  if (overview.isError || !overview.data || !investigationId)
    return (
      <ErrorState
        title="Could not open this investigation"
        message={overview.error instanceof Error ? overview.error.message : undefined}
        onRetry={() => void overview.refetch()}
      />
    );

  const inv = overview.data.investigation;
  const counts = overview.data.counts;

  const tabs: Array<TabItem<TabKey>> = [
    { key: "overview", label: "Overview" },
    { key: "timeline", label: "Timeline", count: undefined },
    { key: "evidence", label: "Evidence", count: counts.evidence },
    { key: "findings", label: "Findings", count: counts.findings },
    { key: "tasks", label: "Tasks", count: counts.tasks },
    { key: "notes", label: "Notes", count: counts.notes },
    { key: "relationships", label: "Relationships" },
    { key: "intelligence", label: "Intelligence" },
    { key: "ai", label: "AI assistant" },
    { key: "reports", label: "Reports", count: counts.reports },
    ...(canAudit ? [{ key: "audit" as TabKey, label: "Audit" }] : []),
  ];

  return (
    <div>
      <Link to="/investigations" className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink-600 hover:text-ink-900">
        <ArrowLeft className="h-4 w-4" /> All investigations
      </Link>

      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-500">{inv.case_ref}</p>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink-950">{inv.title}</h1>
          <p className="mt-1 text-sm text-ink-600">
            Subject: {overview.data.subject_label} · Priority: {priorityLabel(inv.priority)}
            {inv.assigned_to_name ? ` · Assigned to ${inv.assigned_to_name}` : ""}
          </p>
        </div>
      </div>

      <Tabs tabs={tabs} value={tab} onChange={setTab} className="mb-6" />

      {tab === "overview" ? <InvOverview id={investigationId} /> : null}
      {tab === "timeline" ? <InvTimeline id={investigationId} /> : null}
      {tab === "evidence" ? <InvEvidence id={investigationId} /> : null}
      {tab === "findings" ? <InvFindings id={investigationId} /> : null}
      {tab === "tasks" ? <InvTasks id={investigationId} /> : null}
      {tab === "notes" ? <InvNotes id={investigationId} /> : null}
      {tab === "relationships" ? <InvRelationships id={investigationId} /> : null}
      {tab === "intelligence" ? <InvIntelligence id={investigationId} /> : null}
      {tab === "ai" ? <InvAi id={investigationId} /> : null}
      {tab === "reports" ? <InvReports id={investigationId} /> : null}
      {tab === "audit" ? <InvAudit id={investigationId} /> : null}
    </div>
  );
}