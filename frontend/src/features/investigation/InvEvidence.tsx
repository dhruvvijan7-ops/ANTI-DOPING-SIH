import { useState } from "react";
import { FileBox, Plus, ShieldAlert } from "lucide-react";
import {
  useCreateEvidenceMutation,
  useEvidenceListQuery,
  useEvidenceVersionsQuery,
} from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import { EVIDENCE_TYPE_LABELS, SENSITIVITY_META } from "@/lib/constants";
import { formatDate, formatIso, titleCase } from "@/lib/utils";
import type { EvidenceItem } from "@/lib/api/types";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/states";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";

const SENSITIVITY_OPTIONS = ["ROUTINE", "SENSITIVE", "HIGHLY_SENSITIVE", "RESTRICTED"];
const TYPE_OPTIONS = ["DOCUMENT", "TEST", "SCREENSHOT", "STATEMENT", "OTHER"];

export function InvEvidence({ id }: { id: string }) {
  const list = useEvidenceListQuery(id);
  const canCreate = useCan("evidence:create");
  const [selected, setSelected] = useState<EvidenceItem | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const versions = useEvidenceVersionsQuery(id, selected?.id);

  const items = (list.data?.evidence ?? []).filter((e) => !e.deleted);

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
      <Card>
        <CardHeader>
          <CardTitle>Evidence</CardTitle>
          {canCreate ? (
            <Button size="sm" variant="secondary" onClick={() => setShowCreate(true)} leadingIcon={<Plus className="h-4 w-4" />}>
              Add evidence
            </Button>
          ) : null}
        </CardHeader>
        <CardBody>
          {list.isLoading ? (
            <p className="py-8 text-center text-sm text-ink-500">Loading evidence…</p>
          ) : items.length === 0 ? (
            <EmptyState icon={<FileBox className="h-6 w-6" />} title="No evidence logged" description="Documents, test records, statements and captures belong here with full integrity tracking." />
          ) : (
            <ul className="divide-y divide-ink-50">
              {items.map((e) => (
                <li key={e.id}>
                  <button onClick={() => setSelected(e)} className="flex w-full items-center justify-between gap-3 px-2 py-3 text-left hover:bg-ink-50">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink-900">{e.title}</p>
                      <p className="mt-0.5 text-xs text-ink-500">
                        {EVIDENCE_TYPE_LABELS[e.evidence_type] ?? titleCase(e.evidence_type)} · v{e.version}
                        {e.item_date ? ` · ${formatDate(e.item_date)}` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {e.sensitivity === "RESTRICTED" ? <ShieldAlert className="h-4 w-4 text-red-400" /> : null}
                      <Badge tone={e.integrity.verified !== false ? "success" : "danger"}>
                        {e.integrity.verified !== false ? "Integrity verified" : "Integrity check pending"}
                      </Badge>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <aside className="lg:sticky lg:top-24 lg:self-start">
        {selected ? (
          <Card>
            <CardHeader><CardTitle>{selected.sensitivity === "RESTRICTED" ? "Restricted evidence" : selected.title}</CardTitle></CardHeader>
            <CardBody className="space-y-3">
              <p className="text-xs uppercase tracking-wide text-ink-500">
                {EVIDENCE_TYPE_LABELS[selected.evidence_type] ?? selected.evidence_type} · version {selected.version}
              </p>
              <p className="text-sm text-ink-700">{selected.description ?? "No description recorded."}</p>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div><dt className="text-xs text-ink-500">Sensitivity</dt><dd><Badge className={SENSITIVITY_META[selected.sensitivity]?.badge}>{SENSITIVITY_META[selected.sensitivity]?.label ?? selected.sensitivity}</Badge></dd></div>
                <div><dt className="text-xs text-ink-500">Classification</dt><dd>{selected.classification ?? "—"}</dd></div>
                <div><dt className="text-xs text-ink-500">Source</dt><dd className="text-ink-700">{selected.source ?? "—"}</dd></div>
                <div><dt className="text-xs text-ink-500">Item date</dt><dd>{formatDate(selected.item_date)}</dd></div>
              </dl>

              {selected.sensitivity === "RESTRICTED" ? (
                <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  This item is marked RESTRICTED. Content requires elevated access and details are withheld from this view.
                </p>
              ) : (
                <>
                  <IntegrityPanel hashes={selected.integrity.canonical_form} hashValue={selected.integrity.value} verified={selected.integrity.verified !== false} />
                  <VersionsPanel versions={versions.data} loading={versions.isLoading} />
                </>
              )}
            </CardBody>
          </Card>
        ) : (
          <Card><CardBody className="text-center"><p className="text-sm font-medium text-ink-800">Select an item</p><p className="mt-1 text-xs text-ink-500">Version history and integrity details appear here.</p></CardBody></Card>
        )}
      </aside>

      <CreateEvidenceDialog open={showCreate} onClose={() => setShowCreate(false)} investigationId={id} />
    </div>
  );
}

function IntegrityPanel({ hashes, hashValue, verified }: { hashes: string; hashValue: string; verified: boolean }) {
  return (
    <div className="rounded-md border border-ink-100 bg-ink-50/60 p-3 text-xs">
      <p className="mb-1 font-medium text-ink-800">{verified ? "Integrity verified" : "Integrity not yet verified"}</p>
      <p className="break-all font-mono text-[10px] text-ink-500">{hashes}:{hashValue}</p>
      <p className="mt-1 text-ink-500">Canonical integrity form used for tamper-evidence.</p>
    </div>
  );
}

function VersionsPanel({ versions, loading }: { versions: import("@/lib/api/types").EvidenceVersions | undefined; loading: boolean }) {
  if (loading) return <p className="text-xs text-ink-500">Loading version history…</p>;
  if (!versions || versions.count === 0) return <p className="text-xs text-ink-500">No version history recorded.</p>;
  return (
    <div>
      <p className="mb-1 text-xs font-medium text-ink-800">Version history</p>
      <ul className="space-y-1.5 text-xs">
        {[...versions.versions].sort((a, b) => b.version - a.version).map((v) => (
          <li key={v.version} className="flex items-center justify-between gap-2 rounded border border-ink-100 px-2 py-1.5">
            <span className="text-ink-700">v{v.version}</span>
            <span className="truncate text-ink-500">{v.title}</span>
            <span className="shrink-0 text-ink-400">{formatIso(v.created_at)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CreateEvidenceDialog({ open, onClose, investigationId }: { open: boolean; onClose: () => void; investigationId: string }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [evidenceType, setEvidenceType] = useState<string>("DOCUMENT");
  const [source, setSource] = useState("");
  const [classification, setClassification] = useState("");
  const [sensitivity, setSensitivity] = useState("SENSITIVE");
  const [itemDate, setItemDate] = useState("");
  const [relationshipToCase, setRelationshipToCase] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useCreateEvidenceMutation({
    onSuccess: () => { toastSuccess("Evidence recorded."); onClose(); },
    onError: (e) => { const m = e instanceof Error ? e.message : "Failed to add evidence"; setError(m); toastError(m); },
  });

  return (
    <Dialog open={open} onClose={onClose} title="Add evidence" description="Evidence is integrity-hashed on creation and every change is versioned.">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          if (!title.trim()) { setError("Provide a title."); return; }
          create.mutate({
            investigationId,
            body: {
              title: title.trim(),
              description: description.trim() || null,
              evidence_type: evidenceType,
              source: source.trim() || null,
              classification: classification.trim() || null,
              sensitivity,
              item_date: itemDate || null,
              relationship_to_case: relationshipToCase.trim() || null,
            },
          });
        }}
      >
        <Field label="Title" required><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
        <Field label="Description"><Textarea value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Type"><Select value={evidenceType} onChange={(e) => setEvidenceType(e.target.value)}>{TYPE_OPTIONS.map((t) => <option key={t} value={t}>{EVIDENCE_TYPE_LABELS[t] ?? t}</option>)}</Select></Field>
          <Field label="Sensitivity"><Select value={sensitivity} onChange={(e) => setSensitivity(e.target.value)}>{SENSITIVITY_OPTIONS.map((s) => <option key={s} value={s}>{SENSITIVITY_META[s]?.label}</option>)}</Select></Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Source"><Input value={source} onChange={(e) => setSource(e.target.value)} /></Field>
          <Field label="Classification"><Input value={classification} onChange={(e) => setClassification(e.target.value)} /></Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Item date"><Input type="date" value={itemDate} onChange={(e) => setItemDate(e.target.value)} /></Field>
          <Field label="Relationship to case"><Input value={relationshipToCase} onChange={(e) => setRelationshipToCase(e.target.value)} /></Field>
        </div>
        {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={create.isPending}>Add evidence</Button>
        </div>
      </form>
    </Dialog>
  );
}