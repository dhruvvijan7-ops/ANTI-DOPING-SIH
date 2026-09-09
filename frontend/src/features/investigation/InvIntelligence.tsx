import { useInvestigationIntelQuery } from "@/lib/api/queries";
import { formatDate } from "@/lib/utils";
import { infoCategoryLabel } from "@/lib/constants";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";

export function InvIntelligence({ id }: { id: string }) {
  const { data, isLoading, isError, refetch } = useInvestigationIntelQuery(id);

  if (isLoading) return <p className="py-10 text-center text-sm text-ink-500">Loading linked intelligence…</p>;
  if (isError || !data)
    return <p className="py-10 text-center text-sm text-ink-500">Could not load intelligence. <button className="underline" onClick={() => void refetch()}>Retry</button></p>;

  const items = data.intelligence ?? [];

  return (
    <Card>
      <CardHeader><CardTitle>Intelligence linked to this case</CardTitle></CardHeader>
      <CardBody>
        {items.length === 0 ? (
          <EmptyState title="No intelligence linked" description="Reports relevant to the subject are surfaced here for the case team." />
        ) : (
          <ul className="divide-y divide-ink-50">
            {items.map((r) => (
              <li key={r.id} className="py-2.5">
                <p className="text-sm font-medium text-ink-900">{r.title}</p>
                <p className="mt-0.5 text-xs text-ink-500">
                  {infoCategoryLabel(r.info_category)} · {formatDate(r.report_date)}
                </p>
                <div className="mt-1">
                  <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{r.status}</Badge>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}