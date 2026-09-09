import { useState } from "react";
import { MessageSquare, Plus } from "lucide-react";
import { useCreateNoteMutation, useNotesQuery } from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import { formatIso } from "@/lib/utils";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/states";
import { Field, Textarea } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";

export function InvNotes({ id }: { id: string }) {
  const list = useNotesQuery(id);
  const canCreate = useCan("investigations:modify");
  const [draft, setDraft] = useState("");

  const create = useCreateNoteMutation({
    onSuccess: () => { setDraft(""); toastSuccess("Note added."); },
    onError: (e) => toastError(e instanceof Error ? e.message : "Failed to add note"),
  });

  const items = list.data?.notes ?? [];

  return (
    <Card>
      <CardHeader><CardTitle>Investigator notes</CardTitle></CardHeader>
      <CardBody>
        {canCreate ? (
          <form
            className="mb-5 space-y-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (!draft.trim()) return;
              create.mutate({ investigationId: id, body: { content: draft.trim() } });
            }}
          >
            <Field label={undefined}>
              <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Record a note for other investigators…" />
            </Field>
            <div className="flex justify-end">
              <Button type="submit" size="sm" loading={create.isPending} leadingIcon={<Plus className="h-4 w-4" />}>
                Add note
              </Button>
            </div>
          </form>
        ) : null}

        {list.isLoading ? (
          <p className="py-8 text-center text-sm text-ink-500">Loading notes…</p>
        ) : items.length === 0 ? (
          <EmptyState icon={<MessageSquare className="h-6 w-6" />} title="No notes yet" description="Notes track investigational context, decisions and observations as the case develops." />
        ) : (
          <ul className="space-y-3">
            {[...items].reverse().map((n) => (
              <li key={n.id} className="rounded-md border border-ink-100 p-3">
                <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-xs text-ink-500">
                  <span className="font-medium text-ink-700">{n.author}</span>
                  <span>{formatIso(n.created_at)}</span>
                </div>
                <p className="whitespace-pre-wrap text-sm text-ink-800">{n.content}</p>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}