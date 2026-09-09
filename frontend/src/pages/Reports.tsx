import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { investigationsApi, reportsApi } from "@/lib/api/endpoints";
import { priorityLabel } from "@/lib/constants";
import { formatIso } from "@/lib/utils";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { REPORT_STATUS_META } from "@/lib/constants";

interface Row {
  investigation: { id: string; case_ref: string; title: string; priority: string; status: string; updated_at: string };
  reports: Array<{ id: string; version: number; title: string; status: string; purpose: string | null }>;
}

export default function Reports() {
  const query = useQuery({
    queryKey: ["reports", "aggregate"],
    queryFn: async (): Promise<Row[]> => {
      const list = await investigationsApi.list({});
      const invs = list.investigations.slice(0, 10);
      const rows = await Promise.all(
        invs.map(async (inv) => ({
          investigation: {
            id: inv.id,
            case_ref: inv.case_ref,
            title: inv.title,
            priority: inv.priority,
            status: inv.status,
            updated_at: inv.updated_at,
          },
          reports: (await reportsApi.list(inv.id)).reports,
        })),
      );
      return rows;
    },
    staleTime: 60_000,
  });

  return (
    <div>
      <PageHeader
        eyebrow="Case outputs"
        title="Reports"
        description="Final and draft reports across recent investigations. Every report captures the case record, evidence and findings at a point in time."
      />

      {query.isLoading ? <PageLoading label="Loading reports" /> : query.isError ? (
        <ErrorState title="Could not load reports" onRetry={() => void query.refetch()} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState title="No reports available" />
      ) : (
        <div className="space-y-4">
          {query.data?.map((row) => (
            <Card key={row.investigation.id}>
              <CardBody>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-ink-900">
                      <Link to={`/investigations/${row.investigation.id}`} className="hover:text-signal-800">
                        {row.investigation.case_ref} — {row.investigation.title}
                      </Link>
                    </p>
                    <p className="text-xs text-ink-500">
                      {priorityLabel(row.investigation.priority)} · updated {formatIso(row.investigation.updated_at)}
                    </p>
                  </div>
                  <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{row.reports.length} report(s)</Badge>
                </div>
                {row.reports.length === 0 ? (
                  <p className="text-sm text-ink-500">No reports generated for this case yet.</p>
                ) : (
                  <ul className="space-y-1.5">
                    {row.reports.map((r) => (
                      <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-ink-100 px-3 py-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm text-ink-800">{r.title}</p>
                          {r.purpose ? <p className="truncate text-xs text-ink-500">{r.purpose}</p> : null}
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <Badge tone={r.status === "FINAL" ? "success" : r.status === "SUPERSEDED" ? "neutral" : "warn"} className={REPORT_STATUS_META[r.status]?.badge}>
                            {REPORT_STATUS_META[r.status]?.label ?? r.status}
                          </Badge>
                          <span className="text-xs text-ink-400">v{r.version}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}