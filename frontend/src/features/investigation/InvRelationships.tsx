import { useMemo, useState } from "react";
import { Network, Plus } from "lucide-react";
import {
  useCreateRelationshipMutation,
  useIntelligenceSourcesQuery,
  useInvestigationOverviewQuery,
  useInvestigationRelationshipsQuery,
  useRelationshipTypesQuery,
  useSubjectOptionsQuery,
} from "@/lib/api/queries";
import { useCan } from "@/stores/auth";
import type { RelationshipEntityType } from "@/lib/api/types";
import { RelationshipGraphView } from "@/features/relationships/RelationshipGraph";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState, EmptyState } from "@/components/ui/states";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";

const ENTITY_TYPE_OPTIONS: Array<{ value: RelationshipEntityType | string; label: string }> = [
  { value: "ATHLETE", label: "Athlete" },
  { value: "SUPPORT_PERSON", label: "Support person" },
  { value: "TEAM", label: "Team" },
  { value: "ORGANIZATION", label: "Organization" },
  { value: "PROVIDER", label: "Provider" },
  { value: "SUPPLEMENT", label: "Supplement" },
  { value: "EVENT", label: "Event" },
  { value: "COMPETITION", label: "Competition" },
  { value: "LOCATION", label: "Location" },
  { value: "SOURCE", label: "Source" },
];

const BASE_RELATIONSHIP_TYPES = [
  "TEAM_MEMBER",
  "TRAINING_PARTNER",
  "COACH_ATHLETE",
  "MEDICAL_STAFF",
  "TRAVEL_COMPANION",
  "SUPPLEMENT_PROVIDER",
];

export function InvRelationships({ id }: { id: string }) {
  const { data, isLoading, isError, refetch } = useInvestigationRelationshipsQuery(id);
  const canModify = useCan("investigations:modify");
  const canCreateIntel = useCan("intelligence:create");
  const canCreate = canModify || canCreateIntel;
  const [showCreate, setShowCreate] = useState(false);

  if (isLoading) return <p className="py-10 text-center text-sm text-ink-500">Mapping relationships…</p>;
  if (isError || !data) return <ErrorState title="Could not load the relationship map" onRetry={() => void refetch()} />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Relationship map</CardTitle>
        <div className="flex items-center gap-3">
          <span className="text-xs text-ink-500">{data.node_count} nodes · {data.edge_count} connections</span>
          {canCreate ? (
            <Button size="sm" variant="secondary" onClick={() => setShowCreate(true)} leadingIcon={<Plus className="h-4 w-4" />}>
              Add relationship
            </Button>
          ) : null}
        </div>
      </CardHeader>
      <CardBody>
        <RelationshipGraphView graph={data} />
        {data.note ? <p className="mt-2 text-xs text-ink-500">{data.note}</p> : null}
        {data.edges.length === 0 ? (
          <EmptyState icon={<Network className="h-6 w-6" />} title="No connections found" description="Relationships involving this case's subject are mapped here." />
        ) : null}
      </CardBody>
      <CreateRelationshipDialog open={showCreate} onClose={() => setShowCreate(false)} investigationId={id} />
    </Card>
  );
}

function CreateRelationshipDialog({ open, onClose, investigationId }: { open: boolean; onClose: () => void; investigationId: string }) {
  const overview = useInvestigationOverviewQuery(investigationId);
  const typesQuery = useRelationshipTypesQuery(open);
  const sources = useIntelligenceSourcesQuery(open);

  const [targetType, setTargetType] = useState<RelationshipEntityType | string>("ATHLETE");
  const [targetId, setTargetId] = useState("");
  const [search, setSearch] = useState("");
  const [relationshipType, setRelationshipType] = useState("");
  const [confidence, setConfidence] = useState("0.9");
  const [startDate, setStartDate] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const options = useSubjectOptionsQuery(targetType, search, 50);

  const create = useCreateRelationshipMutation({
    onSuccess: () => { toastSuccess("Relationship recorded."); onClose(); },
    onError: (e) => { const m = e instanceof Error ? e.message : "Failed to record relationship"; setError(m); toastError(m); },
  });

  const typeNames = useMemo(() => {
    const fromApi = (typesQuery.data?.types ?? []).map((t) => t.name);
    const set = new Set([...BASE_RELATIONSHIP_TYPES, ...fromApi]);
    return [...set];
  }, [typesQuery.data]);

  const subjectType = overview.data?.investigation.subject_type;
  const subjectId = overview.data?.investigation.subject_id;
  const subjectLabel = overview.data?.subject_label;

  const targetOptions = (options.data?.options ?? []).filter((o) => o.id !== subjectId);

  return (
    <Dialog open={open} onClose={onClose} title="Record relationship">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          if (!subjectType || !subjectId) { setError("This case has no subject to anchor the relationship."); return; }
          if (!targetId) { setError("Select the second entity."); return; }
          if (!relationshipType.trim()) { setError("Select a relationship type."); return; }
          const conf = Number(confidence);
          if (Number.isNaN(conf) || conf < 0 || conf > 1) { setError("Confidence must be between 0 and 1."); return; }
          if (targetId === subjectId) { setError("The case subject cannot be related to itself."); return; }
          create.mutate({
            from_entity_type: subjectType,
            from_entity_id: subjectId,
            to_entity_type: targetType,
            to_entity_id: targetId,
            relationship_type: relationshipType.trim(),
            start_date: startDate || null,
            end_date: null,
            confidence: conf,
            source_id: sourceId || null,
          });
        }}
      >
        <p className="text-xs text-ink-500">
          Records a descriptive association <span className="font-medium text-ink-700">{subjectLabel ?? subjectType}</span> (case subject) ↔ a second entity. Context only — never an assertion of wrongdoing.
        </p>
        <Field id="rel-type" label="Relationship type" required>
          <Select id="rel-type" value={relationshipType} onChange={(e) => setRelationshipType(e.target.value)}>
            <option value="">Select a type…</option>
            {typeNames.map((n) => <option key={n} value={n}>{n}</option>)}
          </Select>
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field id="rel-target-type" label="Second entity type" required>
            <Select id="rel-target-type" value={targetType} onChange={(e) => { setTargetType(e.target.value); setTargetId(""); }}>
              {ENTITY_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </Select>
          </Field>
          <Field id="rel-confidence" label="Confidence (0–1)" hint="Your assessment of how well-founded the association is.">
            <Input id="rel-confidence" type="number" min={0} max={1} step={0.1} value={confidence} onChange={(e) => setConfidence(e.target.value)} />
          </Field>
        </div>
        <Field id="rel-search" label={`Find ${targetType === "ATHLETE" ? "an athlete" : "an entity"}`} description="Search by name or external reference.">
          <Input id="rel-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Type to search…" />
        </Field>
        <Field id="rel-target" label="Select entity" required>
          <Select id="rel-target" value={targetId} onChange={(e) => setTargetId(e.target.value)}>
            <option value="">{options.isLoading ? "Loading…" : "Select an entity…"}</option>
            {targetOptions.map((o) => <option key={o.id} value={o.id}>{o.label}{o.external_ref ? ` (${o.external_ref})` : ""}</option>)}
          </Select>
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field id="rel-start-date" label="Start date (optional)"><Input id="rel-start-date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></Field>
          <Field id="rel-source" label="Source (optional)">
            <Select id="rel-source" value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
              <option value="">No source</option>
              {(sources.data?.sources ?? []).map((s) => <option key={s.source_id} value={s.source_id}>{s.name ?? s.source_type}</option>)}
            </Select>
          </Field>
        </div>
        {error ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={create.isPending}>Record relationship</Button>
        </div>
      </form>
    </Dialog>
  );
}