import { useEffect, useMemo, useState } from "react";
import { useCan } from "@/stores/auth";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";
import { useImportsQuery, useImportDetailQuery, useImportRowsQuery, useImportMappingMutation, useImportCommitMutation, useImportCancelMutation, useUploadImportMutation, usePasteImportMutation } from "@/lib/api/queries";
import type { DataImportItem, ImportStatus } from "@/lib/api/types";
import { formatBytes, formatIso, titleCase } from "@/lib/utils";
import { cn } from "@/lib/utils";

const IMPORT_STATUS_TONE: Record<string, string> = {
  UPLOADED: "bg-ink-100 text-ink-700 ring-ink-200",
  PARSED: "bg-sky-100 text-sky-800 ring-sky-200",
  VALIDATED: "bg-signal-100 text-signal-800 ring-signal-200",
  COMMITTED: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  PARTIAL: "bg-amber-100 text-amber-800 ring-amber-200",
  FAILED: "bg-red-100 text-red-800 ring-red-200",
  CANCELED: "bg-ink-100 text-ink-500 ring-ink-200 line-through",
};

const ROW_STATUS_TONE: Record<string, string> = {
  READY: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  REVIEW: "bg-amber-100 text-amber-800 ring-amber-200",
  DUPLICATE: "bg-ink-100 text-ink-600 ring-ink-200",
  INVALID: "bg-red-100 text-red-800 ring-red-200",
  IMPORTED: "bg-signal-100 text-signal-800 ring-signal-200",
  REJECTED: "bg-ink-100 text-ink-500 ring-ink-200",
};

const SKIP_FIELDS = new Set(["_skip", ""]);

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Request failed";
}

export default function Imports() {
  const canRead = useCan("imports:read");
  const canCreate = useCan("imports:create");
  const canCommit = useCan("imports:commit");

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<ImportStatus>("");

  const list = useImportsQuery({ status: statusFilter || undefined, limit: 100 });
  const detail = useImportDetailQuery(selectedId ?? undefined);

  if (!canRead) {
    return (
      <div>
        <PageHeader
          eyebrow="Import gate"
          title="Data import"
          description="Batch data ingestion is not available to your role."
        />
        <EmptyState title="Access restricted" description="You need the imports:read permission to view data imports." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Import gate"
        title="Data import"
        description="Bring external intelligence records into VERITY. Content is detected from its data (not the filename), validated row-by-row with exact entity matching and dedupe, then committed explicitly."
      />

      {canCreate ? (
        <CreatePanel onCreated={(id) => { setStatusFilter(""); setSelectedId(id); }} />
      ) : (
        <Card>
          <CardBody>
            <p className="text-sm text-ink-500">Your role can review imports but cannot create new ones.</p>
          </CardBody>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
        <Card className="self-start">
          <CardHeader className="items-center justify-between gap-2">
            <CardTitle>Recent imports</CardTitle>
            <Select value={statusFilter} onChange={(e) => setStatusFilter((e.target.value as ImportStatus))} className="h-8 w-36 text-xs" aria-label="Filter by status">
              <option value="">All statuses</option>
              {["PARSED", "VALIDATED", "COMMITTED", "PARTIAL", "FAILED", "CANCELED"].map((s) => (
                <option key={s} value={s}>{titleCase(s)}</option>
              ))}
            </Select>
          </CardHeader>
          <CardBody className="p-0">
            {list.isLoading ? (
              <PageLoading label="Loading imports" />
            ) : list.isError ? (
              <div className="p-4">
                <ErrorState title="Could not load imports" onRetry={() => void list.refetch()} />
              </div>
            ) : list.data && list.data.imports.length === 0 ? (
              <div className="p-4">
                <EmptyState title="No imports yet" description="Upload a file or paste content to begin." />
              </div>
            ) : (
              <ul className="divide-y divide-ink-50">
                {list.data?.imports.map((imp) => (
                  <button
                    key={imp.id}
                    type="button"
                    onClick={() => setSelectedId(imp.id)}
                    className={cn(
                      "block w-full px-4 py-3 text-left transition-colors hover:bg-ink-50",
                      imp.id === selectedId && "bg-signal-50",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-sm font-medium text-ink-900">{imp.name}</p>
                      <StatusBadge>{imp.status}</StatusBadge>
                    </div>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-ink-500">
                      <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{imp.format}</Badge>
                      <span>{imp.source_kind === "PASTE" ? "Paste" : "File"}</span>
                      <span aria-hidden>·</span>
                      <span>{imp.summary?.total ?? 0} rows</span>
                      <span aria-hidden>·</span>
                      <span>{formatIso(imp.created_at)}</span>
                    </div>
                  </button>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <div>
          {selectedId && detail.data ? (
            <ImportWorkspace
              key={detail.data.id}
              data={detail.data}
              canCommit={canCommit}
              canCreate={canCreate}
            />
          ) : detail.isLoading ? (
            <PageLoading label="Loading import details" />
          ) : (
            <Card>
              <CardBody>
                <EmptyState
                  title="Select an import"
                  description="Choose an import from the list to review a preview, adjust the mapping, validate rows, and commit."
                />
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ children }: { children: string }) {
  return (
    <Badge tone="neutral" className={cn("shrink-0", IMPORT_STATUS_TONE[children] ?? "bg-ink-100 text-ink-700 ring-ink-200")}>
      {titleCase(children)}
    </Badge>
  );
}

function RowStatusBadge({ children }: { children: string }) {
  return (
    <Badge tone="neutral" className={cn("shrink-0", ROW_STATUS_TONE[children] ?? "bg-ink-100 text-ink-700 ring-ink-200")}>
      {titleCase(children)}
    </Badge>
  );
}

function CreatePanel({ onCreated }: { onCreated: (id: string) => void }) {
  const [mode, setMode] = useState<"file" | "paste">("file");
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [content, setContent] = useState("");

  const upload = useUploadImportMutation({
    onSuccess: (imp) => {
      toastSuccess(`Imported "${imp.name}" — detected as ${imp.format}.`);
      setFile(null);
      setName("");
      onCreated(imp.id);
    },
    onError: (e) => toastError(errMsg(e)),
  });
  const paste = usePasteImportMutation({
    onSuccess: (imp) => {
      toastSuccess(`Pasted "${imp.name}" — detected as ${imp.format}.`);
      setContent("");
      setName("");
      onCreated(imp.id);
    },
    onError: (e) => toastError(errMsg(e)),
  });

  const busy = upload.isPending || paste.isPending;

  return (
    <Card>
      <CardHeader className="items-center justify-between gap-2">
        <CardTitle>New import</CardTitle>
        <div className="flex gap-1 rounded-md border border-ink-200 p-0.5">
          {(["file", "paste"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={cn(
                "rounded px-3 py-1 text-xs font-medium transition-colors",
                mode === m ? "bg-ink-950 text-paper-50" : "text-ink-600 hover:bg-ink-100",
              )}
            >
              {m === "file" ? "Upload file" : "Paste content"}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardBody>
        {mode === "file" ? (
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (!file) {
                toastError("Choose a file to upload.");
                return;
              }
              upload.mutate({ file, name: name || undefined });
            }}
          >
            <Field id="import-file" label="Data file" description="CSV, TSV, JSON, XLSX, DOCX, PDF, or plain text up to 25 MiB. The format is detected from the content itself.">
              <input
                id="import-file"
                type="file"
                accept=".csv,.tsv,.json,.xlsx,.docx,.pdf,.txt,text/csv,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf,text/plain"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-ink-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-ink-800 hover:file:bg-ink-200"
              />
            </Field>
            {file ? <p className="text-xs text-ink-500">{file.name} — {formatBytes(file.size)}</p> : null}
            <Field id="import-name" label="Display name (optional)">
              <Input id="import-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Lab dispatch 2026-03" maxLength={255} />
            </Field>
            <Button type="submit" variant="secondary" loading={busy} disabled={!file}>
              {busy ? "Uploading…" : "Upload & parse"}
            </Button>
          </form>
        ) : (
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (!content.trim()) {
                toastError("Paste some content first.");
                return;
              }
              paste.mutate({ name: name || "Pasted content", content });
            }}
          >
            <Field id="import-name" label="Display name" required>
              <Input id="import-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Tip line extract" maxLength={255} required />
            </Field>
            <Field id="import-content" label="Content" description="Pasted CSV/JSON/TXT (≤ 5 MiB) is auto-detected and parsed the same way as a file.">
              <Textarea id="import-content" value={content} onChange={(e) => setContent(e.target.value)} rows={8} placeholder={"title,report_date,athlete_ref,info_category\nSighting,2026-01-15,ATH-0012,DOPING"} />
            </Field>
            <Button type="submit" variant="secondary" loading={busy} disabled={!content.trim()}>
              {busy ? "Parsing…" : "Paste & parse"}
            </Button>
          </form>
        )}
      </CardBody>
    </Card>
  );
}

function ImportWorkspace({ data, canCommit, canCreate }: { data: DataImportItem; canCommit: boolean; canCreate: boolean }) {
  const mapping = useImportMappingMutation({
    onSuccess: (updated) => {
      toastSuccess("Mapping applied and rows validated.");
      void refetchDetail();
      void refetchRows();
      return updated;
    },
    onError: (e) => toastError(errMsg(e)),
  });
  const commit = useImportCommitMutation({
    onSuccess: (updated) => {
      toastSuccess(updated.summary.imported > 0
        ? `Committed ${updated.summary.imported} record${updated.summary.imported === 1 ? "" : "s"}.`
        : "No rows were imported — uncommitted rows were left untouched.");
      void refetchDetail();
      void refetchRows();
      void refetchList();
      return updated;
    },
    onError: (e) => toastError(errMsg(e)),
  });
  const cancel = useImportCancelMutation({
    onSuccess: () => {
      toastSuccess("Import canceled.");
      void refetchDetail();
      void refetchList();
    },
    onError: (e) => toastError(errMsg(e)),
  });

  const detailQ = useImportDetailQuery(data.id);
  const rowsQ = useImportRowsQuery(data.id, { limit: 100 });
  const listQ = useImportsQuery({ limit: 100 });
  const refetchDetail = () => detailQ.refetch();
  const refetchRows = () => rowsQ.refetch();
  const refetchList = () => listQ.refetch();

  const current = detailQ.data ?? data;

  const [draftMapping, setDraftMapping] = useState<Record<string, string>>({});
  const [sheetName, setSheetName] = useState<string>(current.sheet_name ?? "");
  const mappingKey = JSON.stringify(current.column_mapping ?? {});
  useEffect(() => {
    setDraftMapping(current.column_mapping ?? {});
    setSheetName(current.sheet_name ?? "");
  }, [current.id, current.column_mapping, mappingKey, current.sheet_name]);

  const [includeReady, setIncludeReady] = useState(true);
  const [includeReview, setIncludeReview] = useState(false);

  const editable = !["COMMITTED", "CANCELED", "FAILED"].includes(current.status);
  const canCommitNow = canCommit && editable && ["VALIDATED", "PARTIAL"].includes(current.status);
  const mappingDirty = JSON.stringify(draftMapping) !== JSON.stringify(current.column_mapping ?? {});

  const onApply = () => {
    const cleaned = Object.fromEntries(Object.entries(draftMapping).filter(([, v]) => !SKIP_FIELDS.has(v)));
    mapping.mutate({
      importId: current.id,
      body: {
        mapping: cleaned,
        sheet_name: current.sheets.length > 1 ? sheetName || null : null,
      },
    });
  };

  const fieldOptions = useMemo(() => [...current.mappable_fields].sort(), [current.mappable_fields]);

  const summary = current.summary;
  const summaryChips: Array<{ label: string; value: number; className?: string }> = [
    { label: "Total", value: summary.total },
    { label: "Ready", value: summary.ready, className: "bg-emerald-100 text-emerald-800" },
    { label: "Review", value: summary.review, className: "bg-amber-100 text-amber-800" },
    { label: "Duplicates", value: summary.duplicates },
    { label: "Invalid", value: summary.invalid, className: "bg-red-100 text-red-800" },
    { label: "Imported", value: summary.imported, className: "bg-signal-100 text-signal-800" },
    { label: "Rejected", value: summary.rejected },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex-row items-center justify-between gap-2">
          <div>
            <CardTitle>{current.name}</CardTitle>
            <p className="mt-0.5 text-xs text-ink-500">
              {current.format}
              {current.source_kind === "PASTE" ? " · pasted" : ` · ${current.source_filename ?? "file"}`}
              {" · "}{formatIso(current.created_at)}
            </p>
          </div>
          <StatusBadge>{current.status}</StatusBadge>
        </CardHeader>
        <CardBody>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-ink-500">Rows</dt>
              <dd className="font-medium text-ink-900">{summary.total}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-500">Structure</dt>
              <dd className="font-medium text-ink-900">{titleCase(current.structure ?? "—")}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-500">File size</dt>
              <dd className="font-medium text-ink-900">{formatBytes(current.file_size)}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-500">SHA-256</dt>
              <dd className="truncate font-mono text-xs text-ink-700" title={current.file_hash ?? ""}>
                {(current.file_hash ?? "—").slice(0, 16)}
              </dd>
            </div>
          </dl>

          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
            {summaryChips.map((c) => (
              <div key={c.label} className="rounded-md border border-ink-100 px-3 py-2">
                <p className="text-xs text-ink-500">{c.label}</p>
                <p className={cn("text-lg font-semibold text-ink-900", c.className)}>{c.value}</p>
              </div>
            ))}
          </div>

          {current.error_message ? (
            <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">{current.error_message}</p>
          ) : null}
        </CardBody>
      </Card>

      {canCreate && editable ? (
        <Card>
          <CardHeader>
            <CardTitle>Column mapping & validation</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            {current.sheets.length > 1 ? (
              <Field id="sheet-name" label="Worksheet" description={`This workbook contains ${current.sheets.length} sheets. Picking one re-parses the file content with that sheet.`}>
                <Select id="sheet-name" value={sheetName} onChange={(e) => setSheetName(e.target.value)}>
                  {current.sheets.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </Select>
              </Field>
            ) : null}

            {current.columns.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-500">
                      <th className="py-2 pr-3">Source column</th>
                      <th className="py-2 pr-3">Inferred type</th>
                      <th className="py-2">Target field</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink-50">
                    {current.columns.map((col) => (
                      <tr key={col}>
                        <td className="py-2 pr-3 font-medium text-ink-900">{col}</td>
                        <td className="py-2 pr-3 text-xs text-ink-500">{titleCase(current.inferred_types?.[col] ?? "—")}</td>
                        <td className="py-2">
                          <Select
                            className="h-8 min-w-44 text-xs"
                            aria-label={`Target field for ${col}`}
                            value={draftMapping[col] ?? "_skip"}
                            onChange={(e) => {
                              const v = e.target.value;
                              setDraftMapping((m) => {
                                const next = { ...m };
                                if (SKIP_FIELDS.has(v)) delete next[col];
                                else next[col] = v;
                                return next;
                              });
                            }}
                          >
                            <option value="_skip">— skip column —</option>
                            {fieldOptions.map((f) => (
                              <option key={f} value={f}>{f}</option>
                            ))}
                          </Select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-ink-500">No columns detected in this source.</p>
            )}

            <div className="flex flex-wrap items-center gap-3">
              <Button variant="secondary" loading={mapping.isPending} disabled={!mappingDirty && !(current.sheets.length > 1)} onClick={onApply}>
                {mapping.isPending ? "Validating…" : "Apply mapping & validate"}
              </Button>
              {summary.total === 0 || summary.parsing_warnings?.length ? (
                <p className="text-xs text-ink-500">{summary.parsing_warnings?.length ? summary.parsing_warnings.join(" · ") : "Validate to see row-by-row results."}</p>
              ) : null}
            </div>
          </CardBody>
        </Card>
      ) : null}

      <Card>
        <CardHeader className="items-center justify-between gap-2">
          <CardTitle>Rows</CardTitle>
          <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{rowsQ.data?.count ?? summary.total} shown</Badge>
        </CardHeader>
        <CardBody className="p-0">
          {rowsQ.isLoading ? (
            <PageLoading label="Loading rows" />
          ) : rowsQ.isError ? (
            <div className="p-4"><ErrorState title="Could not load rows" onRetry={() => void rowsQ.refetch()} /></div>
          ) : rowsQ.data && rowsQ.data.rows.length === 0 ? (
            <div className="p-4"><EmptyState title="No rows" description="No rows match this view." /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-500">
                    <th className="py-2 pl-4 pr-3">#</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Normalized</th>
                    <th className="py-2 pr-3">Entity</th>
                    <th className="py-2 pr-4">Issues</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink-50">
                  {rowsQ.data?.rows.map((row) => (
                    <RowRow key={row.row_number} row={row} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      {canCommitNow ? (
        <Card className="border-signal-200">
          <CardBody className="space-y-3">
            <div className="flex flex-wrap items-center gap-4">
              <p className="text-sm font-medium text-ink-900">Commit selected rows into intelligence:</p>
              <label className="flex items-center gap-1.5 text-sm text-ink-800">
                <input type="checkbox" checked={includeReady} onChange={(e) => setIncludeReady(e.target.checked)} className="h-4 w-4" />
                Ready ({summary.ready})
              </label>
              <label className="flex items-center gap-1.5 text-sm text-ink-800">
                <input type="checkbox" checked={includeReview} onChange={(e) => setIncludeReview(e.target.checked)} className="h-4 w-4" />
                Review ({summary.review})
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                loading={commit.isPending}
                disabled={!includeReady && !includeReview}
                onClick={() => commit.mutate({ importId: current.id, includeStatuses: includeReady && includeReview ? ["READY", "REVIEW"] : includeReady ? ["READY"] : ["REVIEW"] })}
              >
                {commit.isPending ? "Committing…" : "Commit selected rows"}
              </Button>
              <Button variant="ghost" loading={cancel.isPending} disabled={commit.isPending} onClick={() => cancel.mutate({ importId: current.id })}>
                Cancel import
              </Button>
            </div>
          </CardBody>
        </Card>
      ) : current.status === "COMMITTED" || current.status === "PARTIAL" ? (
        <Card>
          <CardBody>
            <p className="text-sm text-ink-500">
              This import has been committed{current.status === "PARTIAL" ? " partially" : ""}; {summary.imported} record{summary.imported === 1 ? "" : "s"} are now in intelligence.
            </p>
          </CardBody>
        </Card>
      ) : null}
    </div>
  );
}

function RowRow({ row }: { row: NonNullable<ReturnType<typeof useImportRowsQuery>["data"]>["rows"][number] }) {
  const title = row.normalized?.title ?? row.original?.title;
  const subject = row.entity_match?.label;
  const issues = [...(row.errors ?? []), ...(row.warnings ?? [])];
  return (
    <tr>
      <td className="py-2 pl-4 pr-3 text-xs text-ink-500">{row.row_number}</td>
      <td className="py-2 pr-3"><RowStatusBadge>{row.status}</RowStatusBadge></td>
      <td className="max-w-56 py-2 pr-3">
        <p className="truncate font-medium text-ink-900" title={String(title ?? "")}>{String(title ?? "—")}</p>
        <p className="truncate text-xs text-ink-500">{row.normalized?.report_date ? String(row.normalized.report_date) : ""}</p>
      </td>
      <td className="py-2 pr-3 text-sm text-ink-700">
        {subject ? <span className="font-medium text-signal-700">{subject}</span> : <span className="text-ink-400">—</span>}
      </td>
      <td className="max-w-64 py-2 pr-4">
        {issues.length > 0 ? (
          <ul className="space-y-0.5">
            {issues.slice(0, 3).map((issue, i) => (
              <li key={i} className={cn("truncate text-xs", (row.errors ?? []).includes(issue) ? "text-red-700" : "text-amber-700")} title={issue}>{issue}</li>
            ))}
          </ul>
        ) : (
          <span className="text-xs text-ink-400">—</span>
        )}
      </td>
    </tr>
  );
}