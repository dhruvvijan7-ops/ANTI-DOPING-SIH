import { useState } from "react";
import { FilePlus2, Plus } from "lucide-react";
import {
  useCreateIntelligenceMutation,
  useIntelligenceSourcesQuery,
  useInvestigationIntelQuery,
  useInvestigationOverviewQuery,
} from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import { infoCategoryLabel } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import type { IntelCreateBody } from "@/lib/api/types";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";

const INFO_CATEGORY_OPTIONS = [
  "SUSPECTED_SUBSTANCE_EXPOSURE",
  "ADMISSION",
  "WITNESS_ACCOUNT",
  "TRAVEL_ANOMALY",
  "MEDICAL_EXCEPTION",
  "SOURCE_OBSERVATION",
];

const RELIABILITY_OPTIONS = [
  { value: "", label: "Not assessed" },
  { value: "A", label: "A — Reliable" },
  { value: "B", label: "B — Usually reliable" },
  { value: "C", label: "C — Fairly reliable" },
];

const CONFIDENTIALITY_OPTIONS = ["INTERNAL", "CONFIDENTIAL", "RESTRICTED", "SECRET"];

const STATUS_OPTIONS = ["NEW", "REVIEWED", "ASSESSED"];

export function InvIntelligence({ id }: { id: string }) {
  const { data, isLoading, isError, refetch } = useInvestigationIntelQuery(id);
  const canCreate = useCan("intelligence:create");
  const [showCreate, setShowCreate] = useState(false);

  if (isLoading) return <p className="py-10 text-center text-sm text-ink-500">Loading linked intelligence…</p>;
  if (isError || !data)
    return <p className="py-10 text-center text-sm text-ink-500">Could not load intelligence. <button className="underline" onClick={() => void refetch()}>Retry</button></p>;

  const items = data.intelligence ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Intelligence linked to this case</CardTitle>
        {canCreate ? (
          <Button size="sm" variant="secondary" onClick={() => setShowCreate(true)} leadingIcon={<Plus className="h-4 w-4" />}>
            Add intelligence
          </Button>
        ) : null}
      </CardHeader>
      <CardBody>
        {items.length === 0 ? (
          <EmptyState
            icon={<FilePlus2 className="h-6 w-6" />}
            title="No intelligence linked"
            description="Reports relevant to the subject are surfaced here for the case team."
          />
        ) : (
          <ul className="divide-y divide-ink-50">
            {items.map((r) => (
              <li key={r.id} className="py-2.5">
                <p className="text-sm font-medium text-ink-900">{r.title}</p>
                <p className="mt-0.5 text-xs text-ink-500">
                  {infoCategoryLabel(r.info_category)} · {formatDate(r.report_date)}
                </p>
                <div className="mt-1">
                  <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{r.status}</Badge>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
      <CreateIntelDialog open={showCreate} onClose={() => setShowCreate(false)} investigationId={id} />
    </Card>
  );
}

function CreateIntelDialog({ open, onClose, investigationId }: { open: boolean; onClose: () => void; investigationId: string }) {
  const sources = useIntelligenceSourcesQuery(true);
  const overview = useInvestigationOverviewQuery(investigationId);
  const [sourceId, setSourceId] = useState("");
  const [title, setTitle] = useState("");
  const [reportDate, setReportDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [infoCategory, setInfoCategory] = useState("SOURCE_OBSERVATION");
  const [reliability, setReliability] = useState("");
  const [confidentiality, setConfidentiality] = useState("INTERNAL");
  const [status, setStatus] = useState("NEW");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useCreateIntelligenceMutation({
    onSuccess: () => { toastSuccess("Intelligence recorded."); onClose(); },
    onError: (e) => { const m = e instanceof Error ? e.message : "Failed to record intelligence"; setError(m); toastError(m); },
  });

  const sourceOptions = sources.data?.sources ?? [];
  const subjectType = overview.data?.investigation.subject_type;
  const subjectId = overview.data?.investigation.subject_id;

  return (
    <Dialog open={open} onClose={onClose} title="Record intelligence">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          if (!sourceId) { setError("Select an intelligence source."); return; }
          if (!title.trim()) { setError("Provide a report title."); return; }
          const body: IntelCreateBody = {
            source_id: sourceId,
            title: title.trim(),
            description: description.trim() || null,
            report_date: reportDate || null,
            info_category: infoCategory,
            reliability: reliability || null,
            confidentiality,
            status,
            subject_type: subjectType,
            subject_id: subjectId,
          };
          create.mutate(body);
        }}
      >
        <p className="text-xs text-ink-500">
          The record is linked to this case&rsquo;s subject{" "}
          <span className="font-medium text-ink-700">{subjectType ?? "—"} / {subjectId ?? "—"}</span>
          , pairing the subject type and id for the engine&rsquo;s cross-source analysis.
        </p>
        <Field id="intel-source" label="Source" required>
          <Select id="intel-source" value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
            <option value="">Select a source…</option>
            {sourceOptions.map((s) => (
              <option key={s.source_id} value={s.source_id}>{s.name ?? s.source_type}{s.external_ref ? ` (${s.external_ref})` : ""}</option>
            ))}
          </Select>
        </Field>
        <Field id="intel-title" label="Title" required><Input id="intel-title" value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field id="intel-report-date" label="Report date"><Input id="intel-report-date" type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} /></Field>
          <Field id="intel-info-category" label="Information category" required>
            <Select id="intel-info-category" value={infoCategory} onChange={(e) => setInfoCategory(e.target.value)}>{INFO_CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{infoCategoryLabel(c)}</option>)}</Select>
          </Field>
          <Field id="intel-reliability" label="Reliability">
            <Select id="intel-reliability" value={reliability} onChange={(e) => setReliability(e.target.value)}>{RELIABILITY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</Select>
          </Field>
          <Field id="intel-confidentiality" label="Confidentiality">
            <Select id="intel-confidentiality" value={confidentiality} onChange={(e) => setConfidentiality(e.target.value)}>{CONFIDENTIALITY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}</Select>
          </Field>
          <Field id="intel-status" label="Status">
            <Select id="intel-status" value={status} onChange={(e) => setStatus(e.target.value)}>{STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}</Select>
          </Field>
        </div>
        <Field id="intel-description" label="Description"><Textarea id="intel-description" value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
        {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={create.isPending}>Record intelligence</Button>
        </div>
      </form>
    </Dialog>
  );
}