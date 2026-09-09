import { useInvestigationAuditQuery } from "@/lib/api/queries";
import { formatIso, titleCase } from "@/lib/utils";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";

export function InvAudit({ id }: { id: string }) {
  const { data, isLoading, isError, refetch } = useInvestigationAuditQuery(id);

  if (isLoading) return <p className="py-10 text-center text-sm text-ink-500">Loading audit trail…</p>;
  if (isError || !data)
    return <p className="py-10 text-center text-sm text-ink-500">Could not load the audit trail. <button className="underline" onClick={() => void refetch()}>Retry</button></p>;

  const rows = [...data.audit].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return (
    <Card>
      <CardHeader><CardTitle>Audit trail</CardTitle></CardHeader>
      <CardBody>
        {rows.length === 0 ? (
          <EmptyState title="No audit events" description="Every action on this case is recorded here without exception." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="py-2 pr-3">Time</th>
                  <th className="py-2 pr-3">Actor</th>
                  <th className="py-2 pr-3">Action</th>
                  <th className="py-2 pr-3">Entity</th>
                  <th className="py-2">Metadata</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-50">
                {rows.map((a) => (
                  <tr key={a.id}>
                    <td className="whitespace-nowrap py-2 pr-3 text-ink-600">{formatIso(a.timestamp)}</td>
                    <td className="py-2 pr-3 text-ink-800">{a.actor}</td>
                    <td className="py-2 pr-3">
                      <Badge tone="neutral" className="bg-ink-100 text-ink-700 ring-ink-200">{titleCase(a.action)}</Badge>
                    </td>
                    <td className="py-2 pr-3 text-xs">{titleCase(a.entity_type)}</td>
                    <td className="max-w-xs truncate px-3 py-2 font-mono text-xs text-ink-500">
                      {Object.keys(a.metadata ?? {}).length ? JSON.stringify(a.metadata) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
}