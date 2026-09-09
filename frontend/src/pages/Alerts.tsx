import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { useAlertsQuery } from "@/lib/api/queries";
import { useAuthStore } from "@/stores/auth";
import { ALERT_STATUS_META, priorityLabel } from "@/lib/constants";
import type { DashboardAlertSummary } from "@/lib/api/types";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/field";
import { PRIORITY_META } from "@/lib/constants";

const ALERT_STATUS_OPTIONS = ["", "NEW", "REVIEWED", "ESCALATED", "CONVERTED", "DISMISSED", "FALSE_POSITIVE"];

export default function Alerts() {
  const [status, setStatus] = useState<string>("");
  const navigate = useNavigate();
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const triageAllowed = hasPermission("alerts:review") || hasPermission("alerts:convert");

  const list = useAlertsQuery({ status: status || null });

  const alerts = list.data?.alerts ?? [];
  const sorted = [...alerts].sort((a, b) => b.score - a.score);

  return (
    <div>
      <PageHeader
        eyebrow="Detection output"
        title="Alert queue"
        description="Every alert reflects one or more scored signals. An alert is a potential concern, not a verdict."
        actions={
          triageAllowed ? (
            <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">
              Triage enabled for your role
            </Badge>
          ) : undefined
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="sr-only" htmlFor="alert-status">Filter by status</label>
        <Select id="alert-status" className="w-56" value={status} onChange={(e) => setStatus(e.target.value)}>
          {ALERT_STATUS_OPTIONS.map((s) => (
            <option key={s || "all"} value={s}>
              {s === "" ? "All statuses" : ALERT_STATUS_META[s]?.label ?? s}
            </option>
          ))}
        </Select>
        <span className="text-xs text-ink-500">
          {list.data ? `${sorted.length} of ${list.data.count}` : "Loading…"}
        </span>
      </div>

      <Card>
        <CardBody>
          {list.isLoading ? (
            <PageLoading label="Loading alerts" />
          ) : list.isError ? (
            <ErrorState title="Could not load alerts" onRetry={() => void list.refetch()} />
          ) : sorted.length === 0 ? (
            <EmptyState
              icon={<AlertTriangle className="h-6 w-6" />}
              title="No alerts in this view"
              description="Run an analysis to generate alerts, or adjust the status filter."
            />
          ) : (
            <ul className="divide-y divide-ink-50">
              {sorted.map((alert) => (
                <li key={alert.id} className="py-3">
                  <button
                    className="flex w-full items-center justify-between gap-3 text-left"
                    onClick={() => navigate(`/alerts/${alert.id}`)}
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium text-ink-900">{alert.title}</p>
                        <StatusBadge alert={alert} />
                      </div>
                      <p className="mt-1 text-xs text-ink-500">
                        {alert.alert_ref} · {priorityLabel(alert.priority_level)} · score {alert.score.toFixed(1)}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span
                        className="h-8 w-1 rounded-full"
                        style={{ backgroundColor: PRIORITY_META[alert.priority_level]?.bar ?? "#94a3b8" }}
                        aria-hidden
                      />
                      <ArrowRight className="h-4 w-4 text-ink-300" />
                    </div>
                  </button>
                  {triageAllowed && alert.status === "NEW" ? (
                    <QuickActions alert={alert} />
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function StatusBadge({ alert }: { alert: DashboardAlertSummary }) {
  const meta = ALERT_STATUS_META[alert.status];
  return <Badge tone={meta?.badge.includes("emerald") ? "success" : meta?.badge.includes("red") ? "danger" : meta?.badge.includes("amber") ? "warn" : "neutral"} className={meta?.badge}>{meta?.label ?? alert.status}</Badge>;
}

function QuickActions({ alert }: { alert: DashboardAlertSummary }) {
  const navigate = useNavigate();
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      <Button size="sm" variant="secondary" onClick={() => navigate(`/alerts/${alert.id}`)}>
        Why flagged
      </Button>
      <Button size="sm" variant="outline" onClick={() => navigate(`/alerts/${alert.id}?action=convert`)}>
        Open for case review
      </Button>
    </div>
  );
}