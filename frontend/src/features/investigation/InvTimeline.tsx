import { useInvestigationTimelineQuery } from "@/lib/api/queries";
import { formatIso, titleCase } from "@/lib/utils";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";

export function InvTimeline({ id }: { id: string }) {
  const { data, isLoading, isError, refetch } = useInvestigationTimelineQuery(id);

  if (isLoading) return <p className="py-10 text-center text-sm text-ink-500">Loading timeline…</p>;
  if (isError || !data)
    return (
      <p className="py-10 text-center text-sm text-ink-500">
        Could not load the timeline. <button className="underline" onClick={() => void refetch()}>Retry</button>
      </p>
    );

  const rows = [...data.timeline].sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime());

  return (
    <Card>
      <CardHeader><CardTitle>Timeline</CardTitle></CardHeader>
      <CardBody>
        {rows.length === 0 ? (
          <EmptyState title="No timeline events" description="Signals, evidence and activity on the case appear here in chronological order." />
        ) : (
          <ol className="relative border-l border-ink-100 pl-6">
            {rows.map((e, i) => (
              <li key={`${e.record_id}-${e.event_type}-${i}`} className="pb-5 last:pb-0">
                <span className="absolute -left-[7px] mt-1 h-3 w-3 rounded-full border-2 border-white bg-signal-600" aria-hidden />
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-ink-900">{e.summary}</p>
                  <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{titleCase(e.event_type)}</Badge>
                </div>
                <p className="mt-1 text-xs text-ink-500">
                  {formatIso(e.occurred_at)} · {e.source} · {e.related_entity}
                </p>
                <p className="mt-1 text-xs text-ink-600">{e.relevance}</p>
              </li>
            ))}
          </ol>
        )}
      </CardBody>
    </Card>
  );
}