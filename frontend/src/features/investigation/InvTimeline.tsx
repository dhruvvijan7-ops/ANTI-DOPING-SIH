import { useState } from "react";
import { CalendarPlus, Plus } from "lucide-react";
import { useCreateTimelineEntryMutation, useInvestigationTimelineQuery } from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import { formatIso, titleCase } from "@/lib/utils";
import type { TimelineEventType } from "@/lib/api/types";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";

const EVENT_TYPE_OPTIONS: Array<{ value: TimelineEventType | string; label: string }> = [
  { value: "MANUAL", label: "Manual note" },
  { value: "MEETING", label: "Meeting" },
  { value: "INTERVIEW", label: "Interview" },
  { value: "SEARCH", label: "Search / request" },
  { value: "OBSERVATION", label: "Observation" },
  { value: "COMMUNICATION", label: "Communication" },
  { value: "LAB_RESULT", label: "Laboratory result" },
  { value: "OTHER", label: "Other" },
];

function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function InvTimeline({ id }: { id: string }) {
  const { data, isLoading, isError, refetch } = useInvestigationTimelineQuery(id);
  const canModify = useCan("investigations:modify");
  const [showAdd, setShowAdd] = useState(false);

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
      <CardHeader>
        <CardTitle>Timeline</CardTitle>
        {canModify ? (
          <Button size="sm" variant="secondary" onClick={() => setShowAdd(true)} leadingIcon={<Plus className="h-4 w-4" />}>
            Add entry
          </Button>
        ) : null}
      </CardHeader>
      <CardBody>
        {rows.length === 0 ? (
          <EmptyState
            icon={<CalendarPlus className="h-6 w-6" />}
            title="No timeline events"
            description="Signals, evidence and activity on the case appear here in chronological order."
          />
        ) : (
          <ol className="relative border-l border-ink-100 pl-6">
            {rows.map((e, i) => (
              <li key={`${e.record_id}-${e.event_type}-${i}`} className="pb-5 last:pb-0">
                <span className="absolute -left-[7px] mt-1 h-3 w-3 rounded-full border-2 border-white bg-signal-600" aria-hidden />
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-ink-900">{e.summary}</p>
                  <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{titleCase(e.event_type)}</Badge>
                  {e.origin === "timeline_events" ? <Badge tone="info">Manual entry</Badge> : null}
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
      <AddEntryDialog open={showAdd} onClose={() => setShowAdd(false)} investigationId={id} />
    </Card>
  );
}

function AddEntryDialog({ open, onClose, investigationId }: { open: boolean; onClose: () => void; investigationId: string }) {
  const [occurredAt, setOccurredAt] = useState(() => toLocalInputValue(new Date()));
  const [eventType, setEventType] = useState<TimelineEventType | string>("MANUAL");
  const [summary, setSummary] = useState("");
  const [source, setSource] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useCreateTimelineEntryMutation({
    onSuccess: () => { toastSuccess("Timeline entry added."); onClose(); },
    onError: (e) => { const m = e instanceof Error ? e.message : "Failed to add entry"; setError(m); toastError(m); },
  });

  return (
    <Dialog open={open} onClose={onClose} title="Add timeline entry">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          if (!summary.trim()) { setError("Provide a summary for this entry."); return; }
          create.mutate({
            investigationId,
            body: {
              occurred_at: new Date(occurredAt).toISOString(),
              event_type: eventType,
              summary: summary.trim(),
              source: source.trim() || null,
            },
          });
        }}
      >
        <Field id="tl-occurred-at" label="When" required><Input id="tl-occurred-at" type="datetime-local" value={occurredAt} onChange={(e) => setOccurredAt(e.target.value)} /></Field>
        <Field id="tl-event-type" label="Event type"><Select id="tl-event-type" value={eventType} onChange={(e) => setEventType(e.target.value)}>{EVENT_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</Select></Field>
        <Field id="tl-summary" label="Summary" required><Textarea id="tl-summary" value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="What happened on the case?" /></Field>
        <Field id="tl-source" label="Source (optional)"><Input id="tl-source" value={source} onChange={(e) => setSource(e.target.value)} placeholder="e.g. case interview, lab report" /></Field>
        {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={create.isPending}>Add entry</Button>
        </div>
      </form>
    </Dialog>
  );
}