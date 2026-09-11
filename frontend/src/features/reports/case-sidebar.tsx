import { useState } from "react";
import { FileText, GitBranch, ListChecks, Lightbulb, MessageSquareText, Timer } from "lucide-react";
import type { DocumentBlock } from "@/lib/api/types";
import {
  useEvidenceListQuery,
  useFindingsQuery,
  useInvestigationOverviewQuery,
  useInvestigationRelationshipsQuery,
  useInvestigationTimelineQuery,
} from "@/lib/api/queries";
import { makeBlock } from "./blocks";
import { formatIso } from "@/lib/utils";

interface CaseSidebarProps {
  investigationId: string;
  onInsertBlocks: (blocks: DocumentBlock[]) => void;
}

type SectionKey = "summary" | "timeline" | "evidence" | "findings" | "relationships" | "intelligence";

const SECTIONS: Array<{ key: SectionKey; label: string; icon: typeof Timer }> = [
  { key: "summary", label: "Case summary", icon: Lightbulb },
  { key: "timeline", label: "Timeline", icon: Timer },
  { key: "evidence", label: "Evidence", icon: FileText },
  { key: "findings", label: "Findings", icon: ListChecks },
  { key: "relationships", label: "Relationships", icon: GitBranch },
  { key: "intelligence", label: "Intelligence", icon: MessageSquareText },
];

export function CaseSidebar({ investigationId, onInsertBlocks }: CaseSidebarProps) {
  const [open, setOpen] = useState<SectionKey>("summary");

  return (
    <aside className="flex h-full min-h-0 flex-col border-l border-ink-100 bg-white">
      <div className="shrink-0 border-b border-ink-100 px-3 py-2">
        <p className="text-sm font-medium text-ink-800">Case intelligence</p>
        <p className="mt-0.5 text-xs text-ink-400">Click an item to insert a grounded section into the report.</p>
      </div>
      <div className="shrink-0 overflow-x-auto border-b border-ink-100 px-1 py-1">
        <div className="flex gap-1">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            const isActive = open === s.key;
            return (
              <button
                key={s.key}
                type="button"
                onClick={() => setOpen(s.key)}
                className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                  isActive ? "bg-ink-900 text-white" : "text-ink-600 hover:bg-ink-100"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {s.label}
              </button>
            );
          })}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {open === "summary" && <SummarySection investigationId={investigationId} onInsertBlocks={onInsertBlocks} />}
        {open === "timeline" && <TimelineSection investigationId={investigationId} onInsertBlocks={onInsertBlocks} />}
        {open === "evidence" && <EvidenceSection investigationId={investigationId} onInsertBlocks={onInsertBlocks} />}
        {open === "findings" && <FindingsSection investigationId={investigationId} onInsertBlocks={onInsertBlocks} />}
        {open === "relationships" && <RelationshipsSection investigationId={investigationId} onInsertBlocks={onInsertBlocks} />}
        {open === "intelligence" && (
          <div className="rounded-md border border-ink-100 bg-ink-50/60 p-3 text-xs text-ink-500">
            Intelligence records for this case are managed on the Intelligence tab of the workspace. Return here to insert
            the grounded sections into your report.
          </div>
        )}
      </div>
    </aside>
  );
}

function InsertButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={`Insert ${label}`}
      aria-label={`Insert ${label}`}
      className="ml-auto shrink-0 rounded bg-ink-900 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-ink-700"
    >
      Insert
    </button>
  );
}

function RowItem({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <li className="flex items-center justify-between gap-2 rounded-md px-2 py-1 hover:bg-ink-50">
      <button type="button" onClick={onClick} className="min-w-0 flex-1 truncate text-left text-xs text-ink-700 hover:text-ink-900" title={label}>
        {label}
      </button>
      <InsertButton onClick={onClick} label="Insert" />
    </li>
  );
}

function SummarySection({ investigationId, onInsertBlocks }: { investigationId: string; onInsertBlocks: (b: DocumentBlock[]) => void }) {
  const { data, isLoading } = useInvestigationOverviewQuery(investigationId);
  if (isLoading) return <p className="text-xs text-ink-400">Loading case…</p>;
  const inv = data?.investigation;
  if (!inv) return <p className="text-xs text-ink-400">Case not found.</p>;
  const insert = () =>
    onInsertBlocks([
      makeBlock("heading", { text: "Case metadata", attrs: { level: 1 } }),
      makeBlock("paragraph", { text: `Case ${inv.case_ref}: ${inv.title}. Status: ${inv.status}, priority ${inv.priority}.` }),
    ]);
  return (
    <div className="space-y-2 text-sm">
      <Info label="Case reference" value={inv.case_ref} />
      <Info label="Title" value={inv.title} />
      <Info label="Status" value={inv.status} />
      <Info label="Priority" value={inv.priority} />
      <div className="pt-2">
        <button type="button" onClick={insert} className="w-full rounded-md bg-ink-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-ink-800">
          Insert case metadata
        </button>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 border-b border-ink-50 pb-1">
      <span className="text-xs text-ink-400">{label}</span>
      <span className="text-xs font-medium text-ink-800">{value}</span>
    </div>
  );
}

function TimelineSection({ investigationId, onInsertBlocks }: { investigationId: string; onInsertBlocks: (b: DocumentBlock[]) => void }) {
  const { data, isLoading } = useInvestigationTimelineQuery(investigationId);
  const items = data?.timeline ?? [];
  if (isLoading) return <p className="text-xs text-ink-400">Loading timeline…</p>;
  if (!items.length) return <p className="text-xs text-ink-400">No timeline events recorded.</p>;
  return (
    <ul className="space-y-1">
      {items.map((item) => {
        const date = formatIso(item.occurred_at);
        const label = `${date} · ${item.event_type}: ${item.summary}`;
        const insert = () =>
          onInsertBlocks([
            makeBlock("paragraph", {
              text: `${date} - ${item.event_type}: ${item.summary} (source: ${item.source || "not recorded"})`,
            }),
          ]);
        return <RowItem key={item.record_id} label={label} onClick={insert} />;
      })}
    </ul>
  );
}

function EvidenceSection({ investigationId, onInsertBlocks }: { investigationId: string; onInsertBlocks: (b: DocumentBlock[]) => void }) {
  const { data, isLoading } = useEvidenceListQuery(investigationId);
  const items = data?.evidence ?? [];
  if (isLoading) return <p className="text-xs text-ink-400">Loading evidence…</p>;
  if (!items.length) return <p className="text-xs text-ink-400">No evidence recorded.</p>;
  return (
    <ul className="space-y-1">
      {items.map((item) => {
        const insert = () =>
          onInsertBlocks([
            makeBlock("paragraph", {
              text: `Evidence: ${item.title} (${item.evidence_type ?? "item"}, ${item.classification ?? "classification not set"})`,
            }),
          ]);
        return <RowItem key={item.id} label={`${item.title} (${item.evidence_type})`} onClick={insert} />;
      })}
    </ul>
  );
}

function FindingsSection({ investigationId, onInsertBlocks }: { investigationId: string; onInsertBlocks: (b: DocumentBlock[]) => void }) {
  const { data, isLoading } = useFindingsQuery(investigationId);
  const items = data?.findings ?? [];
  if (isLoading) return <p className="text-xs text-ink-400">Loading findings…</p>;
  if (!items.length) return <p className="text-xs text-ink-400">No findings recorded.</p>;
  return (
    <ul className="space-y-1">
      {items.map((item) => {
        const insert = () => onInsertBlocks([makeBlock("paragraph", { text: `Finding: ${item.title}: ${item.statement ?? ""}` })]);
        return <RowItem key={item.id} label={item.title} onClick={insert} />;
      })}
    </ul>
  );
}

function RelationshipsSection({ investigationId, onInsertBlocks }: { investigationId: string; onInsertBlocks: (b: DocumentBlock[]) => void }) {
  const { data, isLoading } = useInvestigationRelationshipsQuery(investigationId);
  if (isLoading) return <p className="text-xs text-ink-400">Loading relationships…</p>;
  const edges = data?.edges ?? [];
  if (!edges.length) return <p className="text-xs text-ink-400">No relationships recorded.</p>;
  const nodeLabels = new Map<string, string>((data?.nodes ?? []).map((n) => [n.id, n.label]));
  return (
    <ul className="space-y-1">
      {edges.map((edge) => {
        const rel = edge.data.relationship_type;
        const conf = Math.round((edge.data.confidence ?? 0) * 100);
        const from = nodeLabels.get(edge.source) ?? edge.source;
        const to = nodeLabels.get(edge.target) ?? edge.target;
        const insert = () =>
          onInsertBlocks([
            makeBlock("paragraph", {
              text: `Relationship: ${rel} — ${from} ↔ ${to} (confidence ${conf}%)`,
            }),
          ]);
        return <RowItem key={edge.id} label={`${rel} — ${to}`} onClick={insert} />;
      })}
    </ul>
  );
}