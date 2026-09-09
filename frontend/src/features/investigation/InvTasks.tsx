import { useState } from "react";
import { CheckSquare, Plus } from "lucide-react";
import { useCreateTaskMutation, useTasksQuery, useUpdateTaskMutation } from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import { TASK_STATUS_META } from "@/lib/constants";
import { formatDate, formatIso } from "@/lib/utils";
import type { TaskStatus } from "@/lib/api/types";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/states";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";

const STATUS_OPTIONS: TaskStatus[] = ["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"];

export function InvTasks({ id }: { id: string }) {
  const list = useTasksQuery(id);
  const canModify = useCan("investigations:modify");
  const canCreate = useCan("investigations:modify");
  const [showCreate, setShowCreate] = useState(false);

  const update = useUpdateTaskMutation({
    onSuccess: () => toastSuccess("Task updated."),
    onError: (e) => toastError(e instanceof Error ? e.message : "Update failed"),
  });

  const items = list.data?.tasks ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tasks</CardTitle>
        {canCreate ? (
          <Button size="sm" variant="secondary" onClick={() => setShowCreate(true)} leadingIcon={<Plus className="h-4 w-4" />}>
            Add task
          </Button>
        ) : null}
      </CardHeader>
      <CardBody>
        {list.isLoading ? (
          <p className="py-8 text-center text-sm text-ink-500">Loading tasks…</p>
        ) : items.length === 0 ? (
          <EmptyState icon={<CheckSquare className="h-6 w-6" />} title="No tasks yet" description="Assign actions, deadlines and owners to keep the case moving." />
        ) : (
          <ul className="divide-y divide-ink-50">
            {items.map((t) => (
              <li key={t.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink-900">{t.title}</p>
                  <p className="mt-0.5 text-xs text-ink-500">
                    {t.assigned_to_name ?? "Unassigned"} · {t.due_date ? `due ${formatDate(t.due_date)}` : "no due date"} · created {formatIso(t.created_at)}
                  </p>
                  {t.description ? <p className="mt-1 text-xs text-ink-600">{t.description}</p> : null}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge tone={t.status === "DONE" ? "success" : t.status === "IN_PROGRESS" ? "info" : "neutral"} className={TASK_STATUS_META[t.status]?.badge}>
                    {TASK_STATUS_META[t.status]?.label ?? t.status}
                  </Badge>
                  {canModify ? (
                    <Select
                      aria-label={`Update status for ${t.title}`}
                      className="h-8 w-36 py-1 text-xs"
                      value={String(t.status)}
                      onChange={(e) => update.mutate({ investigationId: id, taskId: t.id, body: { status: e.target.value as TaskStatus } })}
                    >
                      {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{TASK_STATUS_META[s]?.label}</option>)}
                    </Select>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
      <CreateTaskDialog open={showCreate} onClose={() => setShowCreate(false)} investigationId={id} />
    </Card>
  );
}

function CreateTaskDialog({ open, onClose, investigationId }: { open: boolean; onClose: () => void; investigationId: string }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useCreateTaskMutation({
    onSuccess: () => { toastSuccess("Task created."); onClose(); },
    onError: (e) => { const m = e instanceof Error ? e.message : "Failed to create task"; setError(m); toastError(m); },
  });

  return (
    <Dialog open={open} onClose={onClose} title="Add task">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          if (!title.trim()) { setError("Provide a task title."); return; }
          create.mutate({ investigationId, body: { title: title.trim(), description: description.trim() || null, due_date: dueDate || null, status: "OPEN", assigned_to: null } });
        }}
      >
        <Field label="Title" required><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
        <Field label="Description"><Textarea value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
        <Field label="Due date"><Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} /></Field>
        {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={create.isPending}>Create task</Button>
        </div>
      </form>
    </Dialog>
  );
}