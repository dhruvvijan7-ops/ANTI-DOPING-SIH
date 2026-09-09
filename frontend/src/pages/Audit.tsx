import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { investigationsApi } from "@/lib/api/endpoints";
import { formatIso, titleCase } from "@/lib/utils";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";

interface AggregatedEvent {
  id: string;
  investigation: { id: string; case_ref: string; title: string };
  event: import("@/lib/api/types").AuditEvent;
}

export default function Audit() {
  const query = useQuery({
    queryKey: ["audit", "aggregate"],
    queryFn: async (): Promise<AggregatedEvent[]> => {
      const list = await investigationsApi.list({});
      const invs = list.investigations.slice(0, 8);
      const perCase = await Promise.all(
        invs.map(async (inv) => {
          try {
            const audit = await investigationsApi.audit(inv.id);
            return audit.audit.map((event) => ({
              id: event.id,
              investigation: { id: inv.id, case_ref: inv.case_ref, title: inv.title },
              event,
            }));
          } catch {
            return [];
          }
        }),
      );
      return perCase.flat().sort((a, b) => new Date(b.event.timestamp).getTime() - new Date(a.event.timestamp).getTime());
    },
    staleTime: 30_000,
  });

  const rows = query.data ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Immutability record"
        title="Audit log"
        description="A consolidated, tamper-evident record of actions across recent investigations. The full per-case trail is available inside each case."
      />

      <Card>
        <CardBody>
          {query.isLoading ? <PageLoading label="Loading audit log" /> : query.isError ? (
            <ErrorState title="Could not load the audit log" onRetry={() => void query.refetch()} />
          ) : rows.length === 0 ? (
            <EmptyState title="No audit events" description="Actions recorded on cases will appear here." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-500">
                    <th className="py-2 pr-3">Time</th>
                    <th className="py-2 pr-3">Actor</th>
                    <th className="py-2 pr-3">Action</th>
                    <th className="py-2 pr-3">Case</th>
                    <th className="py-2">Entity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink-50">
                  {rows.map((r) => (
                    <tr key={r.id}>
                      <td className="whitespace-nowrap py-2 pr-3 text-ink-600">{formatIso(r.event.timestamp)}</td>
                      <td className="py-2 pr-3 text-ink-800">{r.event.actor}</td>
                      <td className="py-2 pr-3"><Badge tone="neutral" className="bg-ink-100 text-ink-700 ring-ink-200">{titleCase(r.event.action)}</Badge></td>
                      <td className="py-2 pr-3">
                        <Link to={`/investigations/${r.investigation.id}`} className="font-medium text-signal-700 hover:underline">
                          {r.investigation.case_ref}
                        </Link>
                      </td>
                      <td className="py-2 text-xs text-ink-500">{titleCase(r.event.entity_type)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}