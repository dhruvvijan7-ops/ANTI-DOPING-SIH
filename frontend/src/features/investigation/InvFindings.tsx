import { useState } from "react";
import { Link2, Plus } from "lucide-react";
import {
  useCreateFindingMutation,
  useEvidenceListQuery,
  useFindingsQuery,
  useLinkFindingEvidenceMutation,
} from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import { VALIDITY_META } from "@/lib/constants";
import { formatIso } from "@/lib/utils";
import type { FindingItem } from "@/lib/api/types";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/states";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Checkbox } from "@/components/ui/checkbox";
import { toastError, toastSuccess } from "@/components/ui/toasts";

const VALIDITY_OPTIONS = ["SUPPORTING", "CONTRADICTING", "REVIEW"];

export function InvFindings({ id }: { id: string }) {
  const list = useFindingsQuery(id);
  const canCreate = useCan("evidence:create");
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<FindingItem | null>(null);
  const [linkOpen, setLinkOpen] = useState(false);

  const evidence = useEvidenceListQuery(id);
  const evMap = new Map((evidence.data?.evidence ?? []).map((e) => [e.id, e]));

  const items = list.data?.findings ?? [];

  return (
    <div>
      <Card>
        <CardHeader>
          <CardTitle>Findings</CardTitle>
          {canCreate ? (
            <Button size="sm" variant="secondary" onClick={() => setShowCreate(true)} leadingIcon={<Plus className="h-4 w-4" />}>
              Record finding
            </Button>
          ) : null}
        </CardHeader>
        <CardBody>
          {list.isLoading ? (
            <p className="py-8 text-center text-sm text-ink-500">Loading findings…</p>
          ) : items.length === 0 ? (
            <EmptyState title="No findings recorded" description="Analytical conclusions that connect evidence to the investigative question belong here." />
          ) : (
            <ul className="divide-y divide-ink-50">
              {items.map((f) => (
                <li key={f.id} className="py-3">
                  <button className="w-full text-left" onClick={() => setSelected(f)}>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-ink-900">{f.title}</p>
                      <Badge tone={f.confident ? "success" : "warn"}>{f.confident ? "Confident" : "Assessment pending"}</Badge>
                    </div>
                    <p className="mt-1 text-sm text-ink-700">{f.statement}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {f.evidence_links.map((l) => {
                        const ev = evMap.get(l.evidence_id);
                        return (
                          <Badge key={l.link_id} tone={VALIDITY_META[l.validity]?.badge.includes("red") ? "danger" : VALIDITY_META[l.validity]?.badge.includes("emerald") ? "success" : "neutral"} className={VALIDITY_META[l.validity]?.badge}>
                            {ev?.title ?? l.evidence_id.slice(0, 8)} · {VALIDITY_META[l.validity]?.label ?? l.validity}
                          </Badge>
                        );
                      })}
                      {f.evidence_links.length === 0 ? <span className="text-xs text-ink-400">No evidence linked</span> : null}
                    </div>
                  </button>
                  {selected?.id === f.id ? (
                    <div className="mt-3 rounded-md border border-ink-100 bg-ink-50/50 p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-ink-500">Assessment</p>
                      <p className="mt-1 text-sm text-ink-700">{f.assessment ?? "No assessment recorded."}</p>
                      <p className="mt-2 text-xs text-ink-500">Author: {f.author} · Updated {formatIso(f.updated_at)}</p>
                      {canCreate ? (
                        <Button size="sm" variant="outline" className="mt-3" onClick={() => setLinkOpen(true)} leadingIcon={<Link2 className="h-4 w-4" />}>
                          Link evidence
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <CreateFindingDialog open={showCreate} onClose={() => setShowCreate(false)} investigationId={id} />
      {selected ? (
        <LinkEvidenceDialog
          open={linkOpen}
          onClose={() => setLinkOpen(false)}
          investigationId={id}
          finding={selected}
          evidenceOptions={(evidence.data?.evidence ?? []).filter((e) => !e.deleted)}
        />
      ) : null}
    </div>
  );
}

function CreateFindingDialog({ open, onClose, investigationId }: { open: boolean; onClose: () => void; investigationId: string }) {
  const [title, setTitle] = useState("");
  const [statement, setStatement] = useState("");
  const [supportingEvidence, setSupportingEvidence] = useState("");
  const [assessment, setAssessment] = useState("");
  const [confident, setConfident] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCreateFindingMutation({
    onSuccess: () => { toastSuccess("Finding recorded."); onClose(); },
    onError: (e) => { const m = e instanceof Error ? e.message : "Failed to save finding"; setError(m); toastError(m); },
  });

  return (
    <Dialog open={open} onClose={onClose} title="Record a finding" description="State what the case has established so far, referencing the evidence that supports it.">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          if (!title.trim() || !statement.trim()) { setError("Provide a title and a statement."); return; }
          create.mutate({
            investigationId,
            body: {
              title: title.trim(),
              statement: statement.trim(),
              supporting_evidence: supportingEvidence.trim() || null,
              assessment: assessment.trim() || null,
              confident,
            },
          });
        }}
      >
        <Field label="Title" required><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
        <Field label="Statement" required description="A concise, defensible statement of what the records currently indicate.">
          <Textarea value={statement} onChange={(e) => setStatement(e.target.value)} />
        </Field>
        <Field label="Supporting evidence summary"><Textarea value={supportingEvidence} onChange={(e) => setSupportingEvidence(e.target.value)} /></Field>
        <Field label="Assessment"><Textarea value={assessment} onChange={(e) => setAssessment(e.target.value)} /></Field>
        <label className="flex items-center gap-2 text-sm text-ink-800">
          <Checkbox checked={confident} onChange={(e) => setConfident(e.target.checked)} />
          I am confident in this finding at this stage
        </label>
        {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={create.isPending}>Save finding</Button>
        </div>
      </form>
    </Dialog>
  );
}

function LinkEvidenceDialog({ open, onClose, investigationId, finding, evidenceOptions }: {
  open: boolean;
  onClose: () => void;
  investigationId: string;
  finding: FindingItem;
  evidenceOptions: import("@/lib/api/types").EvidenceItem[];
}) {
  const [evidenceId, setEvidenceId] = useState("");
  const [validity, setValidity] = useState("SUPPORTING");
  const [error, setError] = useState<string | null>(null);

  const link = useLinkFindingEvidenceMutation({
    onSuccess: () => { toastSuccess("Evidence linked to finding."); onClose(); },
    onError: (e) => {
      const m = e instanceof Error ? e.message : "Failed to link evidence";
      setError(m);
      toastError(m);
    },
  });

  return (
    <Dialog open={open} onClose={onClose} title={`Link evidence — ${finding.title}`} description="State whether this item supports or contradicts the finding.">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          if (!evidenceId) { setError("Select an evidence item."); return; }
          link.mutate({ investigationId, findingId: finding.id, evidenceId, validity });
        }}
      >
        <Field label="Evidence item" required>
          <Select value={evidenceId} onChange={(e) => setEvidenceId(e.target.value)}>
            <option value="">Select…</option>
            {evidenceOptions.map((ev) => (
              <option key={ev.id} value={ev.id}>{ev.title}</option>
            ))}
          </Select>
        </Field>
        <Field label="Validity">
          <Select value={validity} onChange={(e) => setValidity(e.target.value)}>
            {VALIDITY_OPTIONS.map((v) => <option key={v} value={v}>{VALIDITY_META[v]?.label}</option>)}
          </Select>
        </Field>
        {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={link.isPending}>Link evidence</Button>
        </div>
      </form>
    </Dialog>
  );
}