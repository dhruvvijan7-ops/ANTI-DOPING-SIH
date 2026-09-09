import { Link } from "react-router-dom";
import { ArrowRight, Bell, FileText, FolderOpen, ShieldAlert, Users2 } from "lucide-react";
import { formatIso, timeAgo } from "@/lib/utils";
import { ALERT_STATUS_META, priorityLabel } from "@/lib/constants";
import { useDashboardQuery } from "@/lib/api/queries";
import type { Dashboard } from "@/lib/api/types";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody, CardHeader, CardTitle, StatCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/states";
import { PageLoading, ErrorState } from "@/components/ui/states";

export default function Dashboard() {
  const { data, isLoading, isError, refetch } = useDashboardQuery();

  if (isLoading) return <PageLoading label="Loading dashboard" />;
  if (isError || !data) return <ErrorState title="Could not load the dashboard" message="The platform did not return dashboard data." onRetry={() => void refetch()} />;

  const totalOpen = data.investigations.open ?? 0;
  const alertsTotal = data.alerts.total ?? 0;
  const intelTotal = data.intelligence.reports_total ?? 0;
  const newReports = data.intelligence.new_reports ?? 0;

  return (
    <div>
      <PageHeader
        eyebrow="Operational overview"
        title="Dashboard"
        description="A current view of the intelligence and investigation workload across the platform."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Open investigations"
          value={totalOpen}
          hint={`${data.investigations.total} total`}
          icon={<FolderOpen className="h-5 w-5" />}
        />
        <StatCard
          label="Active alerts"
          value={alertsTotal}
          hint="Requiring triage review"
          icon={<ShieldAlert className="h-5 w-5" />}
        />
        <StatCard
          label="Intelligence reports"
          value={intelTotal}
          hint={`${newReports} ingested recently`}
          icon={<FileText className="h-5 w-5" />}
        />
        <StatCard
          label="Athletes profiled"
          value={data.entities.athletes_total}
          hint="Across all disciplines"
          icon={<Users2 className="h-5 w-5" />}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <AlertQueue alerts={data.alerts} />
        <InvestigationList items={data.investigations} />
      </div>

      <div className="mt-6">
        <RecentIntel items={data.intelligence} />
      </div>
    </div>
  );
}

function AlertQueue({ alerts }: { alerts: Dashboard["alerts"] }) {
  const prioritySorted = [...alerts.recent].sort((a, b) => b.score - a.score);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Alerts awaiting review</CardTitle>
        <Link to="/alerts" className="inline-flex items-center gap-1 text-sm font-medium text-signal-700 hover:text-signal-800">
          Review queue <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </CardHeader>
      <CardBody>
        {prioritySorted.length === 0 ? (
          <EmptyState icon={<Bell className="h-6 w-6" />} title="No alerts in the queue" description="New alerts appear here when a detection run generates them." />
        ) : (
          <ul className="divide-y divide-ink-50">
            {prioritySorted.slice(0, 6).map((alert) => (
              <li key={alert.id} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <Link to={`/alerts/${alert.id}`} className="block truncate text-sm font-medium text-ink-900 hover:text-signal-800">
                    {alert.title}
                  </Link>
                  <p className="mt-0.5 text-xs text-ink-500">
                    {alert.alert_ref} · {timeAgo(alert.created_at)} · {priorityLabel(alert.priority_level)}
                  </p>
                </div>
                <Badge tone={ALERT_STATUS_META[alert.status]?.badge ? "warn" : "neutral"} className={ALERT_STATUS_META[alert.status]?.badge}>
                  {ALERT_STATUS_META[alert.status]?.label ?? alert.status}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

function InvestigationList({ items }: { items: Dashboard["investigations"] }) {
  const recent = [...(items.recent ?? [])].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent investigations</CardTitle>
        <Link to="/investigations" className="inline-flex items-center gap-1 text-sm font-medium text-signal-700 hover:text-signal-800">
          All cases <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </CardHeader>
      <CardBody>
        {recent.length === 0 ? (
          <EmptyState icon={<FolderOpen className="h-6 w-6" />} title="No investigations yet" description="Investigations created from alerts or intelligence appear here." />
        ) : (
          <ul className="divide-y divide-ink-50">
            {recent.slice(0, 6).map((inv) => (
              <li key={inv.id} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <Link to={`/investigations/${inv.id}`} className="block truncate text-sm font-medium text-ink-900 hover:text-signal-800">
                    {inv.case_ref} — {inv.title}
                  </Link>
                  <p className="mt-0.5 text-xs text-ink-500">
                    {priorityLabel(inv.priority)} · updated {formatIso(inv.updated_at)}
                    {inv.assigned_to_name ? ` · ${inv.assigned_to_name}` : ""}
                  </p>
                </div>
                <Badge tone="neutral" className="bg-emerald-50 text-emerald-800 ring-emerald-200">Open</Badge>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

function RecentIntel({ items }: { items: Dashboard["intelligence"] }) {
  const recent = items.recent ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recently ingested intelligence</CardTitle>
        <Link to="/intelligence" className="inline-flex items-center gap-1 text-sm font-medium text-signal-700 hover:text-signal-800">
          Intelligence feed <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </CardHeader>
      <CardBody>
        {recent.length === 0 ? (
          <EmptyState icon={<FileText className="h-6 w-6" />} title="No intelligence reports" />
        ) : (
          <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {recent.slice(0, 6).map((item) => (
              <li key={item.id} className="rounded-md border border-ink-100 px-3 py-2.5">
                <p className="truncate text-sm font-medium text-ink-900">{item.title}</p>
                <p className="mt-0.5 text-xs text-ink-500">
                  {item.subject_name} · {item.info_category?.replaceAll("_", " ").toLowerCase()} · {timeAgo(item.ingestion_date)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}