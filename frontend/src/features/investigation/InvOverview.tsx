import { useState } from "react";
import { Link } from "react-router-dom";
import {
  useAssignInvestigationMutation,
  useCloseInvestigationMutation,
  useInvestigationOverviewQuery,
  useUpdateInvestigationMutation,
} from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import { INVESTIGATION_STATUS_META, PRIORITY_ORDER, priorityLabel } from "@/lib/constants";
import { formatIso } from "@/lib/utils";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";

export function InvOverview({ id }: { id: string }) {
  const overview = useInvestigationOverviewQuery(id);
  const canModify = useCan("investigations:modify");
  const canAssign = useCan("investigations:assign");

  const close = useCloseInvestigationMutation({
    onSuccess: (data) => toastSuccess(`${data.case_ref} closed.`),
    onError: (e) => toastError(e instanceof Error ? e.message : "Close failed"),
  });

  const [editOpen, setEditOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);

  if (overview.isLoading || !overview.data) {
    return (
      <p className="py-10 text-center text-sm text-ink-500">
        {overview.isError ? "Could not load case overview." : "Loading…"}
      </p>
    );
  }

  const inv = overview.data.investigation;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{inv.case_ref} — {inv.title}</CardTitle>
          <div className="flex flex-wrap gap-2">
            {canModify ? <Button size="sm" variant="outline" onClick={() => setEditOpen(true)}>Edit details</Button> : null}
            {canAssign ? <Button size="sm" variant="secondary" onClick={() => setAssignOpen(true)}>Assign case</Button> : null}
            {inv.status === "OPEN" && canModify ? (
              <Button size="sm" variant="ghost" onClick={() => close.mutate({ id })}>Close case</Button>
            ) : null}
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge tone={inv.status === "OPEN" ? "success" : "neutral"} className={INVESTIGATION_STATUS_META[inv.status]?.badge}>
              {INVESTIGATION_STATUS_META[inv.status]?.label ?? inv.status}
            </Badge>
            <Badge tone="warn" className="bg-amber-50 text-amber-800 ring-amber-200">{priorityLabel(inv.priority)}</Badge>
            {inv.originating_alert_id ? (
              <Link to={`/alerts/${inv.originating_alert_id}`}>
                <Badge tone="info">Linked to source alert</Badge>
              </Link>
            ) : null}
          </div>

          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs text-ink-500">Subject</dt>
              <dd className="font-medium text-ink-900">{overview.data.subject_label}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-500">Assigned to</dt>
              <dd className="font-medium text-ink-900">{inv.assigned_to_name ?? "Unassigned"}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-500">Created</dt>
              <dd className="text-ink-700">{formatIso(inv.created_at)}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-500">Last updated</dt>
              <dd className="text-ink-700">{formatIso(inv.updated_at)}</dd>
            </div>
          </dl>
        </CardBody>
      </Card>

      <Card>
        <CardHeader><CardTitle>Case contents</CardTitle></CardHeader>
        <CardBody>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Count label="Alerts" value={overview.data.counts.alerts} />
            <Count label="Evidence" value={overview.data.counts.evidence} />
            <Count label="Findings" value={overview.data.counts.findings} />
            <Count label="Tasks" value={overview.data.counts.tasks} />
            <Count label="Notes" value={overview.data.counts.notes} />
            <Count label="Reports" value={overview.data.counts.reports} />
          </div>
        </CardBody>
      </Card>

      {overview.data.originating_alert ? (
        <Card>
          <CardHeader><CardTitle>Origin</CardTitle></CardHeader>
          <CardBody>
            <p className="text-sm text-ink-700">
              This case was opened from alert <span className="font-medium">{overview.data.originating_alert.alert_ref}</span>{" "}
              ({priorityLabel(overview.data.originating_alert.priority_level)}, score {overview.data.originating_alert.score.toFixed(1)}) generated{" "}
              {formatIso(overview.data.originating_alert.created_at)}.
            </p>
            <Link to={`/alerts/${overview.data.originating_alert.alert_id}`} className="mt-2 inline-flex h-8 items-center rounded-md px-3 text-sm font-medium text-signal-700 ring-1 ring-inset ring-signal-200 hover:bg-signal-50">
              Review the original alert analysis
            </Link>
          </CardBody>
        </Card>
      ) : null}

      {editOpen ? (
        <EditDialog id={id} initial={{ title: inv.title, priority: inv.priority }} onClose={() => setEditOpen(false)} />
      ) : null}
      {assignOpen ? (
        <AssignDialog id={id} onClose={() => setAssignOpen(false)} onAssigned={() => void overview.refetch()} />
      ) : null}
    </div>
  );
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-ink-100 p-3 text-center">
      <p className="text-xl font-semibold tabular-nums text-ink-950">{value}</p>
      <p className="text-xs text-ink-500">{label}</p>
    </div>
  );
}

function EditDialog({ id, initial, onClose }: { id: string; initial: { title: string; priority: string }; onClose: () => void }) {
  const [title, setTitle] = useState(initial.title);
  const [priority, setPriority] = useState(initial.priority);
  const [description, setDescription] = useState("");
  const update = useUpdateInvestigationMutation({
    onSuccess: () => { toastSuccess("Case updated."); onClose(); },
    onError: (e) => toastError(e instanceof Error ? e.message : "Update failed"),
  });
  return (
    <form
      className="mt-4 space-y-3 rounded-md border border-ink-100 bg-ink-50/50 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        update.mutate({ id, body: { title, priority, description: description || null } });
      }}
    >
      <Field label="Title"><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
      <Field label="Priority"><Select value={priority} onChange={(e) => setPriority(e.target.value)}>{PRIORITY_ORDER.map((p) => <option key={p} value={p}>{priorityLabel(p)}</option>)}</Select></Field>
      <Field label="Description" hint="Editing the description requires the case tools; it is supported for new cases."><Textarea value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button type="submit" loading={update.isPending}>Save changes</Button>
      </div>
    </form>
  );
}

function AssignDialog({ id, onClose, onAssigned }: { id: string; onClose: () => void; onAssigned: () => void }) {
  const [note, setNote] = useState("");
  const assign = useAssignInvestigationMutation({
    onSuccess: () => { toastSuccess("Case assigned."); onAssigned(); onClose(); },
    onError: (e) => toastError(e instanceof Error ? e.message : "Assignment failed"),
  });
  return (
    <form
      className="mt-4 space-y-3 rounded-md border border-ink-100 bg-ink-50/50 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        assign.mutate({ id, body: { assigned_to: null, note: note || null } });
      }}
    >
      <p className="text-sm text-ink-700">Reassigns the case to the current investigator's team queue, clearing the previous assignee.</p>
      <Field label="Assignment note (optional)"><Textarea value={note} onChange={(e) => setNote(e.target.value)} /></Field>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button type="submit" loading={assign.isPending}>Confirm assignment</Button>
      </div>
    </form>
  );
}