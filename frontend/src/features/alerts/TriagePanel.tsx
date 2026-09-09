import { useState } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  useConvertAlertMutation,
  useDismissAlertMutation,
  useEscalateAlertMutation,
  useFalsePositiveAlertMutation,
  useReviewAlertMutation,
} from "@/lib/api/queries";
import type { DashboardAlertSummary } from "@/lib/api/types";
import { useAuthStore, useCan } from "@/stores/auth";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { PRIORITY_ORDER, priorityLabel } from "@/lib/constants";
import { toastError, toastSuccess } from "@/components/ui/toasts";

export function TriagePanel({ alert, onConverted }: { alert: DashboardAlertSummary; onConverted?: (invId: string) => void }) {
  const [modal, setModal] = useState<"" | "convert" | "note">("");
  const [priority, setPriority] = useState<string>(alert.priority_level ?? "HIGH");
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const canReview = useCan("alerts:review");
  const canDismiss = useCan("alerts:dismiss");
  const canConvert = useCan("alerts:convert");

  const invalidation = () => {
    void qc.invalidateQueries({ queryKey: ["dashboard"] });
    void qc.invalidateQueries({ queryKey: ["alerts"] });
    void qc.invalidateQueries({ queryKey: ["alerts", alert.id, "detail"] });
  };

  const review = useReviewAlertMutation({
    onSuccess: () => toastSuccess("Alert marked as reviewed."),
    onError: (e) => toastError(e instanceof Error ? e.message : "Review failed"),
    onSettled: invalidation,
  });
  const dismiss = useDismissAlertMutation({
    onSuccess: () => toastSuccess("Alert dismissed."),
    onError: (e) => toastError(e instanceof Error ? e.message : "Dismissal failed"),
    onSettled: invalidation,
  });
  const falsePositive = useFalsePositiveAlertMutation({
    onSuccess: () => toastSuccess("Alert recorded as a false positive."),
    onError: (e) => toastError(e instanceof Error ? e.message : "Update failed"),
    onSettled: invalidation,
  });
  const escalate = useEscalateAlertMutation({
    onSuccess: () => toastSuccess("Alert escalated."),
    onError: (e) => toastError(e instanceof Error ? e.message : "Escalation failed"),
    onSettled: invalidation,
  });
  const convert = useConvertAlertMutation({
    onSuccess: (data) => {
      toastSuccess(`Investigation ${data.investigation.case_ref} created.`);
      onConverted?.(data.investigation.id);
    },
    onError: (e) => toastError(e instanceof Error ? e.message : "Conversion failed"),
    onSettled: invalidation,
  });

  const submitConvert = () => {
    convert.mutate({
      alertId: alert.id,
      body: {
        priority,
        title: title.trim() || undefined,
        note: note.trim() || null,
        assigned_to: priority === "HIGH" && user?.role?.permissions?.some((p) => p.key === "investigations:assign") ? null : null,
      },
    });
    setModal("");
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {canReview && alert.status === "NEW" ? (
        <Button size="sm" variant="secondary" loading={review.isPending} onClick={() => review.mutate({ alertId: alert.id })}>
          Mark reviewed
        </Button>
      ) : null}
      {canReview && (alert.status === "NEW" || alert.status === "REVIEWED") ? (
        <Button size="sm" variant="outline" loading={escalate.isPending} onClick={() => escalate.mutate({ alertId: alert.id })}>
          Escalate
        </Button>
      ) : null}
      {canDismiss && alert.status === "NEW" ? (
        <Button size="sm" variant="outline" loading={dismiss.isPending} onClick={() => dismiss.mutate({ alertId: alert.id })}>
          Dismiss
        </Button>
      ) : null}
      {canDismiss && (alert.status === "NEW" || alert.status === "REVIEWED") ? (
        <Button size="sm" variant="ghost" loading={falsePositive.isPending} onClick={() => falsePositive.mutate({ alertId: alert.id })}>
          Mark false positive
        </Button>
      ) : null}
      {canConvert && alert.investigation_id ? (
        <Link to={`/investigations/${alert.investigation_id}`}>
          <Button size="sm" variant="primary">Open linked case</Button>
        </Link>
      ) : canConvert && (alert.status === "NEW" || alert.status === "REVIEWED" || alert.status === "ESCALATED") ? (
        <Button size="sm" variant="primary" onClick={() => setModal("convert")}>
          Convert to investigation
        </Button>
      ) : null}

      <Dialog open={modal === "convert"} onClose={() => setModal("")} title="Convert to investigation" description="Creates a case record linked to this alert. A priority level does not imply a verdict about the subject.">
        <div className="space-y-4">
          <Field id="convert-title" label="Title override (optional)">
            <Input id="convert-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder={`Default: ${alert.title}`} />
          </Field>
          <Field id="convert-priority" label="Priority" description="Initial investigation priority.">
            <Select id="convert-priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
              {PRIORITY_ORDER.map((p) => (
                <option key={p} value={p}>{priorityLabel(p)}</option>
              ))}
            </Select>
          </Field>
          <Field id="convert-note" label="Triage note (optional)">
            <Textarea id="convert-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Context for investigators…" />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setModal("")}>Cancel</Button>
            <Button onClick={submitConvert} loading={convert.isPending}>Create investigation</Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}