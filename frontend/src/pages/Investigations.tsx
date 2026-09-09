import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { FolderOpen, Plus } from "lucide-react";
import { investigationsApi, athletesApi } from "@/lib/api/endpoints";
import { useInvestigationsQuery } from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import { INVESTIGATION_STATUS_META, PRIORITY_ORDER, priorityLabel } from "@/lib/constants";
import { formatIso } from "@/lib/utils";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Dialog } from "@/components/ui/dialog";
import { toastError, toastSuccess } from "@/components/ui/toasts";

const STATUS_OPTIONS = ["", "OPEN", "CLOSED", "ARCHIVED"];

export default function Investigations() {
  const [status, setStatus] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const navigate = useNavigate();
  const canCreate = useCan("investigations:create");

  const list = useInvestigationsQuery({ status: status || null });
  const investigations = list.data?.investigations ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Case management"
        title="Investigations"
        description="Formal case records built from alerts or intelligence, tracked through assignment, evidence, findings and reporting."
        actions={
          canCreate ? (
            <Button variant="secondary" onClick={() => setShowCreate(true)} leadingIcon={<Plus className="h-4 w-4" />}>
              New investigation
            </Button>
          ) : undefined
        }
      />

      <div className="mb-4">
        <label className="sr-only" htmlFor="inv-status">Filter by status</label>
        <Select id="inv-status" className="w-56" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s || "all"} value={s}>{s === "" ? "All statuses" : INVESTIGATION_STATUS_META[s]?.label ?? s}</option>
          ))}
        </Select>
      </div>

      <Card>
        <CardBody>
          {list.isLoading ? <PageLoading label="Loading cases" /> : list.isError ? (
            <ErrorState title="Could not load investigations" onRetry={() => void list.refetch()} />
          ) : investigations.length === 0 ? (
            <EmptyState icon={<FolderOpen className="h-6 w-6" />} title="No investigations" description="Cases created from alerts or new case records appear here." />
          ) : (
            <ul className="divide-y divide-ink-50">
              {investigations.map((inv) => (
                <li key={inv.id}>
                  <button
                    onClick={() => navigate(`/investigations/${inv.id}`)}
                    className="flex w-full items-center justify-between gap-3 px-2 py-3 text-left transition-colors hover:bg-ink-50"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium text-ink-900">{inv.case_ref}</p>
                        <p className="truncate text-sm text-ink-700">{inv.title}</p>
                        <Badge tone={INVESTIGATION_STATUS_META[inv.status]?.badge.includes("emerald") ? "success" : inv.status === "CLOSED" ? "neutral" : "warn"} className={INVESTIGATION_STATUS_META[inv.status]?.badge}>
                          {INVESTIGATION_STATUS_META[inv.status]?.label ?? inv.status}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-ink-500">
                        {priorityLabel(inv.priority)} · created {formatIso(inv.created_at)}
                        {inv.assigned_to_name ? ` · assigned to ${inv.assigned_to_name}` : " · unassigned"}
                      </p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <Dialog open={showCreate} onClose={() => setShowCreate(false)} title="New investigation" description="Create a case record. You can link it to a source alert later.">
        <CreateForm onDone={(id) => { setShowCreate(false); navigate(`/investigations/${id}`); }} />
      </Dialog>
    </div>
  );
}

function CreateForm({ onDone }: { onDone: (id: string) => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("MODERATE");
  const [subjectType, setSubjectType] = useState<"ATHLETE" | "SUPPORT_PERSON">("ATHLETE");
  const [subjectId, setSubjectId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const qc = useQueryClient();

  const subjects = useQuery({ queryKey: ["subjects-for-create"], queryFn: () => athletesApi.list({ limit: 200 }) });

  const create = useMutation({
    mutationFn: () =>
      investigationsApi.create({
        title: title.trim(),
        description: description.trim() || null,
        priority,
        subject_type: subjectType,
        subject_id: subjectId,
        assigned_to: null,
      }),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ["investigations"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
      toastSuccess(`${data.case_ref} created.`);
      onDone(data.id);
    },
    onError: (e) => {
      const msg = e instanceof Error ? e.message : "Creation failed";
      setError(msg);
      toastError(msg);
    },
  });

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        if (!title.trim() || !subjectId) {
          setError("Provide a title and select the subject.");
          return;
        }
        create.mutate();
      }}
    >
      <Field label="Title" id="inv-title" required>
        <Input id="inv-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Case title" />
      </Field>
      <Field label="Description">
        <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Summary of the concern and scope…" />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Priority" id="inv-priority">
          <Select id="inv-priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
            {PRIORITY_ORDER.map((p) => <option key={p} value={p}>{priorityLabel(p)}</option>)}
          </Select>
        </Field>
        <Field label="Subject type" id="inv-subject-type">
          <Select id="inv-subject-type" value={subjectType} onChange={(e) => setSubjectType(e.target.value as "ATHLETE" | "SUPPORT_PERSON")}>
            <option value="ATHLETE">Athlete</option>
            <option value="SUPPORT_PERSON">Support person</option>
          </Select>
        </Field>
      </div>
      <Field
        label={subjectType === "ATHLETE" ? "Athlete" : "Support person"}
        id="inv-subject"
        hint={subjectType === "SUPPORT_PERSON" ? "Choose from the athlete list; support persons are covered by their associated profiles." : undefined}
      >
        <Select id="inv-subject" value={subjectId} onChange={(e) => setSubjectId(e.target.value)} disabled={subjects.isLoading}>
          <option value="">Select subject…</option>
          {(subjects.data?.athletes ?? []).map((a) => (
            <option key={a.id} value={a.id}>{a.full_name} ({a.external_ref})</option>
          ))}
        </Select>
      </Field>

      {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => onDone("")}>Cancel</Button>
        <Button type="submit" loading={create.isPending}>Create investigation</Button>
      </div>
    </form>
  );
}