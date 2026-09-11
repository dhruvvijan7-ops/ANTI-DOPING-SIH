import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, FileText, Pencil, Plus, Send } from "lucide-react";
import {
  useCreateReportMutation,
  usePublishReportMutation,
  useReportsQuery,
} from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import { REPORT_STATUS_META } from "@/lib/constants";
import type { ReportItem } from "@/lib/api/types";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/states";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Textarea } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";

export function InvReports({ id }: { id: string }) {
  const navigate = useNavigate();
  const list = useReportsQuery(id);
  const canGenerate = useCan("reports:generate");
  const [showCreate, setShowCreate] = useState(false);
  const [viewing, setViewing] = useState<ReportItem | null>(null);

  const items = [...(list.data?.reports ?? [])].sort((a, b) => b.version - a.version);

  const openEditor = (r: ReportItem) => navigate(`/investigations/${r.investigation_id}/reports/${r.id}/edit`);

  return (
    <div>
      <Card>
        <CardHeader>
          <CardTitle>Reports</CardTitle>
          {canGenerate ? (
            <Button size="sm" variant="secondary" onClick={() => setShowCreate(true)} leadingIcon={<Plus className="h-4 w-4" />}>
              New report
            </Button>
          ) : null}
        </CardHeader>
        <CardBody>
          {list.isLoading ? (
            <p className="py-8 text-center text-sm text-ink-500">Loading reports…</p>
          ) : items.length === 0 ? (
            <EmptyState icon={<FileText className="h-6 w-6" />} title="No reports yet" description="Drafts are generated from case evidence either manually or with the grounded AI assistant." />
          ) : (
            <ul className="divide-y divide-ink-50">
              {items.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-ink-900">{r.title}</p>
                      <Badge tone={r.status === "FINAL" ? "success" : r.status === "SUPERSEDED" ? "neutral" : "warn"} className={REPORT_STATUS_META[r.status]?.badge}>
                        {REPORT_STATUS_META[r.status]?.label ?? r.status}
                      </Badge>
                      <Badge tone="neutral" className="bg-ink-100 text-ink-500 ring-ink-200">v{r.version}</Badge>
                    </div>
                    <p className="mt-0.5 text-xs text-ink-500">{r.purpose ?? "No purpose statement set."}</p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Published r={r} />
                    <Button size="sm" variant="outline" onClick={() => openEditor(r)} leadingIcon={<Pencil className="h-4 w-4" />}>
                      Open
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setViewing(r)} leadingIcon={<Eye className="h-4 w-4" />}>
                      Summary
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <CreateReportDialog open={showCreate} onClose={() => setShowCreate(false)} investigationId={id} />
      <Dialog open={Boolean(viewing)} onClose={() => setViewing(null)} title={viewing?.title ?? "Report"} width="max-w-3xl">
        {viewing ? <ReportSectionsView report={viewing} /> : null}
      </Dialog>
    </div>
  );
}

function Published({ r }: { r: ReportItem }) {
  const canGenerate = useCan("reports:generate");
  const [pending, setPending] = useState(false);
  const publish = usePublishReportMutation({
    onSuccess: () => { toastSuccess("Report finalised. Any previous final version was superseded."); setPending(false); },
    onError: (e) => { toastError(e instanceof Error ? e.message : "Publish failed"); setPending(false); },
  });
  if (r.status !== "DRAFT" || !canGenerate) return <Button size="sm" variant="ghost" disabled>Published</Button>;
  return (
    <Button
      size="sm"
      variant="secondary"
      loading={pending}
      onClick={() => { setPending(true); publish.mutate({ investigationId: r.investigation_id, reportId: r.id }); }}
      leadingIcon={<Send className="h-4 w-4" />}
    >
      Finalise
    </Button>
  );
}

function ReportSectionsView({ report }: { report: ReportItem }) {
  const s = report.sections;
  return (
    <div className="space-y-4 text-sm">
      <div className="rounded-md border border-ink-100 bg-ink-50/60 p-3">
        <p className="text-xs uppercase tracking-wide text-ink-500">Case</p>
        <p className="font-medium text-ink-900">{s.case_metadata.case_ref} — {s.case_metadata.title}</p>
        <p className="text-xs text-ink-500">{s.case_metadata.status} · priority {s.case_metadata.priority} · {s.case_metadata.subject}</p>
      </div>
      <Section title="Purpose" body={report.purpose ?? s.purpose} />
      <Section title="Evidence" body={(s.evidence ?? []).join("\n")} />
      <Section title="Findings" body={(s.findings ?? []).join("\n")} />
      <Section title="Unresolved questions" body={(s.unresolved_questions ?? []).join("\n")} />
      <Section title="Outcome" body={report.outcome ?? s.outcome} />
      {s.audit_metadata ? (
        <div className="rounded-md border border-ink-100 p-3 text-xs text-ink-600">
          Audit metadata: {s.audit_metadata.recorded_audit_events} events · {s.audit_metadata.notes_count} notes · {s.audit_metadata.tasks_count} tasks at generation.
        </div>
      ) : null}
    </div>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  if (!body) return null;
  return (
    <div>
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-500">{title}</h3>
      <div className="whitespace-pre-wrap text-ink-800">{body}</div>
    </div>
  );
}

function CreateReportDialog({ open, onClose, investigationId }: { open: boolean; onClose: () => void; investigationId: string }) {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [purpose, setPurpose] = useState("");
  const [outcome, setOutcome] = useState("");
  const [questions, setQuestions] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useCreateReportMutation({
    onSuccess: (data) => {
      toastSuccess("Draft report created. Opening the editor…");
      onClose();
      navigate(`/investigations/${investigationId}/reports/${data.id}/edit`);
    },
    onError: (e) => { const m = e instanceof Error ? e.message : "Failed to create report"; setError(m); toastError(m); },
  });

  return (
    <Dialog open={open} onClose={onClose} title="New report draft" description="The draft captures case metadata automatically; you set the purpose and open questions.">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          create.mutate({
            investigationId,
            body: {
              title: title.trim() || null,
              purpose: purpose.trim() || null,
              outcome: outcome.trim() || null,
              unresolved_questions: questions ? questions.split("\n").map((q) => q.trim()).filter(Boolean) : null,
            },
          });
        }}
      >
        <Field label="Title (optional)"><Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Defaults to the case title" /></Field>
        <Field label="Purpose"><Textarea value={purpose} onChange={(e) => setPurpose(e.target.value)} /></Field>
        <Field label="Outcome (optional)"><Textarea value={outcome} onChange={(e) => setOutcome(e.target.value)} /></Field>
        <Field label="Unresolved questions (one per line)"><Textarea value={questions} onChange={(e) => setQuestions(e.target.value)} /></Field>
        {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={create.isPending}>Create draft</Button>
        </div>
      </form>
    </Dialog>
  );
}