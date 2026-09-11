import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Archive,
  ArrowLeft,
  CheckCircle2,
  CloudOff,
  CopyPlus,
  Download,
  Loader2,
  Save,
  Send,
  Sparkles,
} from "lucide-react";
import type { BlockProvenanceKind, DocumentBlock, ReportType } from "@/lib/api/types";
import {
  useAiDraftReportMutation,
  useAiSectionReportMutation,
  useArchiveReportMutation,
  usePublishReportMutation,
  useReportDetailQuery,
  useReviewReportMutation,
  useSaveReportDocumentMutation,
  useSetReportTypeMutation,
  useUpdateReportMutation,
} from "@/lib/api/queries";
import { reportExportApi } from "@/lib/api/endpoints";
import { REPORT_STATUS_META, REPORT_TYPE_META } from "@/lib/constants";
import { toastError, toastSuccess } from "@/components/ui/toasts";
import { PageLoading } from "@/components/ui/spinner";
import { ErrorState } from "@/components/ui/states";
import { BlockEditor } from "./block-editor";
import { CaseSidebar } from "./case-sidebar";
import { EditorToolbar } from "./toolbar";
import { countWords, lastSavedLabel, makeBlock } from "./blocks";

const LOCKED = new Set(["FINAL", "SUPERSEDED", "ARCHIVED"]);

const AI_SECTIONS: Array<{ slug: string; label: string }> = [
  { slug: "timeline", label: "Timeline summary" },
  { slug: "evidence", label: "Evidence table" },
  { slug: "findings", label: "Findings" },
  { slug: "intelligence", label: "Intelligence assessment" },
  { slug: "relationships", label: "Relationship summary" },
  { slug: "gaps", label: "Information gaps" },
  { slug: "questions", label: "Investigative questions" },
  { slug: "assessment", label: "Analytical assessment" },
];

function getErr(e: unknown): string {
  if (e && typeof e === "object" && "message" in e) return String((e as { message: unknown }).message);
  return String(e);
}

function withProvenance(b: DocumentBlock, kind: BlockProvenanceKind): DocumentBlock {
  return { ...b, provenance: b.provenance ?? { kind, refs: [] } };
}

interface ReportsEditorProps {
  investigationId: string;
  reportId: string;
}

export function ReportsEditor({ investigationId, reportId }: ReportsEditorProps) {
  const navigate = useNavigate();
  const detail = useReportDetailQuery(investigationId, reportId);

  const [blocks, setBlocks] = useState<DocumentBlock[]>([]);
  const [title, setTitle] = useState("");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const initializedRef = useRef(false);
  const saveInFlightRef = useRef(false);
  const lastSavedRef = useRef<string>("");

  const saveDocument = useSaveReportDocumentMutation();
  const updateReport = useUpdateReportMutation();
  const aiDraftMut = useAiDraftReportMutation();
  const aiSectionMut = useAiSectionReportMutation();
  const setTypeMut = useSetReportTypeMutation();
  const reviewMut = useReviewReportMutation();
  const publishMut = usePublishReportMutation();
  const archiveMut = useArchiveReportMutation();

  const report = detail.data;
  const status = String(report?.status ?? "DRAFT");
  const locked = LOCKED.has(status);

  // Hydrate editor state from the report (prefer the latest autosaved draft).
  useEffect(() => {
    if (!report || initializedRef.current) return;
    const draft = (report.draft ?? []).filter((b) => b && b.id).map((b) => withProvenance(b, b.provenance?.kind ?? "human"));
    const persisted = (report.blocks ?? []).filter((b) => b && b.id).map((b) => withProvenance(b, b.provenance?.kind ?? "human"));
    const source = draft.length ? draft : persisted;
    setBlocks(source);
    setTitle(report.title ?? "");
    initializedRef.current = true;
    lastSavedRef.current = JSON.stringify({ title: report.title, blocks: source });
  }, [report]);

  const blocksRef = useRef<DocumentBlock[]>(blocks);
  const titleRef = useRef<string>(title);
  blocksRef.current = blocks;
  titleRef.current = title;

  const changedSignature = useMemo(() => JSON.stringify({ title, blocks }), [title, blocks]);
  const dirty = changedSignature !== lastSavedRef.current;

  // Debounced autosave (1.2s) for editable reports (draft-only, never destroys persisted text).
  useEffect(() => {
    if (!initializedRef.current || locked || !dirty || saveInFlightRef.current) return;
    const t = setTimeout(() => {
      const snapshot = { title: titleRef.current, blocks: blocksRef.current };
      const sig = JSON.stringify(snapshot);
      saveInFlightRef.current = true;
      void saveDocument
        .mutateAsync({ investigationId, reportId, body: { ...snapshot, autosave: true } })
        .then(() => {
          lastSavedRef.current = sig;
          setSavedAt(new Date().toISOString());
        })
        .catch((e) => toastError(`Autosave failed: ${getErr(e)}`))
        .finally(() => {
          saveInFlightRef.current = false;
        });
    }, 1200);
    return () => clearTimeout(t);
  }, [changedSignature, locked, dirty, saveDocument, investigationId, reportId]);

  if (detail.isLoading) return <PageLoading label="Loading report editor" />;
  if (detail.isError || !report)
    return <ErrorState title="Could not load report" message={detail.error instanceof Error ? detail.error.message : undefined} />;

  const insertBlocks = (incoming: DocumentBlock[]) => {
    if (locked) return;
    setBlocks((prev) => [...prev, ...incoming]);
  };

  const addBlock = (type: DocumentBlock["type"], attrs?: Record<string, unknown>) => {
    if (locked) return;
    const b = makeBlock(type, attrs);
    setBlocks((prev) => {
      const idx = activeId ? prev.findIndex((x) => x.id === activeId) : -1;
      if (idx >= 0) {
        const next = [...prev];
        next.splice(idx + 1, 0, b);
        setActiveId(b.id);
        return next;
      }
      return [...prev, b];
    });
  };

  const insertAfter = (id: string) => {
    const b = makeBlock("paragraph");
    setBlocks((prev) => {
      const idx = prev.findIndex((x) => x.id === id);
      const next = [...prev];
      next.splice(idx + 1, 0, b);
      return next;
    });
    setActiveId(b.id);
  };

  const removeBlock = (id: string) => {
    if (locked) return;
    setBlocks((prev) => prev.filter((b) => b.id !== id));
    if (activeId === id) setActiveId(null);
  };

  const changeBlock = (id: string, patch: Partial<DocumentBlock>) => {
    if (locked) return;
    setBlocks((prev) =>
      prev.map((b) => {
        if (b.id !== id) return b;
        const next = { ...b, ...patch };
        if (b.provenance?.kind === "ai" && (patch.text !== undefined || patch.items || patch.rows || patch.head)) {
          next.provenance = { kind: "ai_edited", refs: b.provenance.refs ?? [] };
        }
        return next;
      }),
    );
  };

  const toggleAttr = (key: string, value: unknown) => {
    if (!activeId) return;
    changeBlock(activeId, { attrs: { ...(blocks.find((b) => b.id === activeId)?.attrs ?? {}), [key]: value } });
  };

  const persist = async () => {
    if (locked) return;
    setBusy(true);
    try {
      const snapshot = { title, blocks };
      const sig = JSON.stringify(snapshot);
      const res = await saveDocument.mutateAsync({ investigationId, reportId, body: { ...snapshot, autosave: false } });
      if (String(res.id) !== reportId) {
        toastSuccess("Created new version");
        navigate(`/investigations/${investigationId}/reports/${res.id}/edit`);
        return;
      }
      lastSavedRef.current = sig;
      setSavedAt(new Date().toISOString());
      toastSuccess("Report saved");
    } catch (e) {
      toastError(`Save failed: ${getErr(e)}`);
    } finally {
      setBusy(false);
    }
  };

  const runAiDraft = async () => {
    setBusy(true);
    try {
      const res = await aiDraftMut.mutateAsync({ investigationId, reportId });
      const mapped = (res.blocks ?? []).filter((b) => b && b.id).map((b) => withProvenance(b, "ai"));
      lastSavedRef.current = JSON.stringify({ title: res.title, blocks: mapped });
      setBlocks(mapped);
      setTitle(res.title ?? titleRef.current);
      setSavedAt(new Date().toISOString());
      toastSuccess("AI draft generated");
    } catch (e) {
      toastError(`AI draft failed: ${getErr(e)}`);
    } finally {
      setBusy(false);
    }
  };

  const runAiSection = async (slug: string) => {
    try {
      const res = await aiSectionMut.mutateAsync({ investigationId, reportId, section: slug });
      const incoming = (res.blocks ?? []).filter((b) => b && b.id).map((b) => withProvenance(b, "ai"));
      setBlocks((prev) => [...prev, ...incoming]);
      toastSuccess(`Inserted ${res.label}`);
    } catch (e) {
      toastError(`AI section failed: ${getErr(e)}`);
    }
  };

  const runAction = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toastSuccess(ok);
    } catch (e) {
      toastError(`${ok} failed: ${getErr(e)}`);
    }
  };

  const newVersion = async () => {
    setBusy(true);
    try {
      const res = await updateReport.mutateAsync({
        investigationId,
        reportId,
        body: { title: titleRef.current, purpose: report.purpose, outcome: report.outcome },
      });
      if (String(res.id) !== reportId) {
        toastSuccess("Created new draft version");
        navigate(`/investigations/${investigationId}/reports/${res.id}/edit`);
      } else {
        toastSuccess("Report updated");
      }
    } catch (e) {
      toastError(`New version failed: ${getErr(e)}`);
    } finally {
      setBusy(false);
    }
  };

  const exportAs = async (kind: "html" | "docx" | "pdf") => {
    try {
      const res = await reportExportApi[kind](investigationId, reportId);
      toastSuccess(`Exported ${res.filename}`);
    } catch (e) {
      toastError(`Export failed: ${getErr(e)}`);
    }
  };

  const statusMeta = REPORT_STATUS_META[status] ?? { label: status, badge: "" };
  const typeLabel = REPORT_TYPE_META[String(report.report_type)]?.label ?? String(report.report_type);
  const wordCount = countWords(blocks);
  const activeBlock = blocks.find((b) => b.id === activeId) ?? null;

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <header className="shrink-0 border-b border-ink-100 bg-white">
        <div className="flex items-center gap-3 px-4 py-2">
          <Link to={`/investigations/${investigationId}`} className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-600 hover:text-ink-900">
            <ArrowLeft className="h-4 w-4" /> Back to case
          </Link>
          <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ring-1 ${statusMeta.badge || "bg-ink-100 text-ink-700 ring-ink-200"}`}>
            {statusMeta.label}
          </span>
          <span className="rounded bg-ink-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ink-500">
            v{report.version} · {typeLabel}
          </span>
          <span className="ml-auto text-xs text-ink-400">
            {wordCount} words ·{" "}
            {locked ? (
              <span className="inline-flex items-center gap-1">
                <CloudOff className="h-3 w-3" /> Read only
              </span>
            ) : (
              lastSavedLabel(savedAt ?? report.draft_saved_at)
            )}
          </span>
        </div>

        {locked && (
          <div className="flex items-center justify-between gap-2 border-t border-ink-100 bg-ink-50/70 px-4 py-1.5 text-xs text-ink-600">
            <span>
              This report is <b>{status.toLowerCase()}</b> and locked for editing. Export a copy, or create a new version to continue.
            </span>
            {report.status !== "ARCHIVED" && (
              <button
                type="button"
                onClick={() => void newVersion()}
                disabled={busy}
                className="inline-flex items-center gap-1 rounded bg-ink-900 px-2 py-1 text-xs font-medium text-white hover:bg-ink-700 disabled:opacity-50"
              >
                {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <CopyPlus className="h-3 w-3" />} Create new version
              </button>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 border-t border-ink-100 px-4 py-2">
          <div className="min-w-0 flex-1">
            <input
              value={title}
              onChange={(e) => !locked && setTitle(e.target.value)}
              placeholder="Report title"
              disabled={locked}
              className="w-full rounded-md border border-transparent bg-transparent px-2 py-1 text-base font-semibold text-ink-900 outline-none focus:border-ink-200 focus:bg-white"
            />
          </div>
          <button
            type="button"
            onClick={() => void persist()}
            disabled={locked || !dirty || busy}
            className="inline-flex items-center gap-1 rounded-md bg-ink-900 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-ink-700 disabled:opacity-40"
          >
            <Save className="h-3.5 w-3.5" /> Save
          </button>
          <button
            type="button"
            onClick={() => void runAiDraft()}
            disabled={locked || busy}
            title="Regenerate the whole document as a grounded AI draft"
            className="inline-flex items-center gap-1 rounded-md bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />} AI draft
          </button>
          <select
            value=""
            onChange={(e) => e.target.value && void runAiSection(e.target.value)}
            disabled={locked}
            className="rounded-md border border-ink-200 bg-white px-2 py-1.5 text-xs font-medium text-ink-700 hover:border-ink-300"
          >
            <option value="">AI section…</option>
            {AI_SECTIONS.map((s) => (
              <option key={s.slug} value={s.slug}>{s.label}</option>
            ))}
          </select>
          <select
            value={String(report.report_type)}
            onChange={(e) => void setTypeMut.mutate({ investigationId, reportId, reportType: e.target.value as ReportType })}
            disabled={locked || setTypeMut.isPending}
            title="Report type"
            className="rounded-md border border-ink-200 bg-white px-2 py-1.5 text-xs font-medium text-ink-700"
          >
            <option value="MANUAL">Manual</option>
            <option value="AI_ASSISTED">AI-assisted</option>
            <option value="HYBRID">Hybrid</option>
          </select>
          {status === "DRAFT" && (
            <button
              type="button"
              onClick={() => void runAction(() => reviewMut.mutateAsync({ investigationId, reportId }), "Sent to review")}
              className="inline-flex items-center gap-1 rounded-md border border-ink-200 bg-white px-2.5 py-1.5 text-xs font-medium text-ink-700 hover:bg-ink-50"
            >
              <Send className="h-3.5 w-3.5" /> Send to review
            </button>
          )}
          {status === "IN_REVIEW" && (
            <button
              type="button"
              onClick={() => void runAction(() => publishMut.mutateAsync({ investigationId, reportId }), "Report published")}
              className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-500"
            >
              <CheckCircle2 className="h-3.5 w-3.5" /> Publish
            </button>
          )}
          {status === "DRAFT" && (
            <button
              type="button"
              onClick={() => void runAction(() => archiveMut.mutateAsync({ investigationId, reportId }), "Report archived")}
              className="inline-flex items-center gap-1 rounded-md border border-ink-200 bg-white px-2.5 py-1.5 text-xs font-medium text-ink-700 hover:bg-ink-50"
            >
              <Archive className="h-3.5 w-3.5" /> Archive
            </button>
          )}
          <div className="flex items-center gap-1 border-l border-ink-100 pl-2">
            <span className="mr-1 inline-flex items-center gap-1 text-xs text-ink-400">
              <Download className="h-3.5 w-3.5" /> Export
            </span>
            <button type="button" onClick={() => void exportAs("html")} className="rounded border border-ink-200 bg-white px-2 py-1 text-xs font-medium text-ink-700 hover:bg-ink-50">
              HTML
            </button>
            <button type="button" onClick={() => void exportAs("docx")} className="rounded border border-ink-200 bg-white px-2 py-1 text-xs font-medium text-ink-700 hover:bg-ink-50">
              DOCX
            </button>
            <button type="button" onClick={() => void exportAs("pdf")} className="rounded border border-ink-200 bg-white px-2 py-1 text-xs font-medium text-ink-700 hover:bg-ink-50">
              PDF
            </button>
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 bg-ink-50/60">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <EditorToolbar onAddBlock={addBlock} activeBlock={activeBlock} onToggleAttr={toggleAttr} />
          <div className="min-h-0 flex-1 overflow-y-auto p-6">
            <div className="mx-auto max-w-3xl">
              <div className="rounded-lg border border-ink-100 bg-white p-8 shadow-sm">
                <BlockEditor
                  blocks={blocks}
                  activeId={activeId}
                  onActive={setActiveId}
                  onChange={changeBlock}
                  onInsertAfter={insertAfter}
                  onRemove={removeBlock}
                />
              </div>
              <p className="mt-3 text-center text-xs text-ink-400">
                {locked ? "Export a copy to download the final document with its citation and provenance." : `Document · ${wordCount} words · v${report.version}`}
              </p>
            </div>
          </div>
        </div>
        <CaseSidebar investigationId={investigationId} onInsertBlocks={insertBlocks} />
      </div>
    </div>
  );
}