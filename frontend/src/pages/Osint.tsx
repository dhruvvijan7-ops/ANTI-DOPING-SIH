import { useState } from "react";
import { Radar, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { useCan } from "@/stores/auth";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { Field, Input, Select } from "@/components/ui/field";
import { toastError, toastSuccess } from "@/components/ui/toasts";
import {
  useOsintCollectSourceMutation,
  useOsintCollectTargetedMutation,
  useOsintConnectorTypesQuery,
  useOsintCreateClaimMutation,
  useOsintCreateSourceMutation,
  useOsintDeleteSourceMutation,
  useOsintDedupeClusterQuery,
  useOsintPromoteMutation,
  useOsintRecordDetailQuery,
  useOsintRecordsQuery,
  useOsintReviewClaimMutation,
  useOsintSeedDefaultsMutation,
  useOsintSourcesQuery,
  useOsintUpdateSourceMutation,
} from "@/lib/api/queries";
import type { OsintCollectSummary, OsintRecordItem, OsintSourceCreateBody } from "@/lib/api/types";
import { cn, formatIso, titleCase } from "@/lib/utils";

const HEALTH_TONE: Record<string, string> = {
  ACTIVE: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  DEGRADED: "bg-amber-100 text-amber-800 ring-amber-200",
  FAILED: "bg-red-100 text-red-800 ring-red-200",
  RATE_LIMITED: "bg-orange-100 text-orange-800 ring-orange-200",
  DISABLED: "bg-ink-100 text-ink-500 ring-ink-200",
};

const VERIFY_TONE: Record<string, string> = {
  UNREVIEWED: "bg-ink-100 text-ink-600 ring-ink-200",
  REVIEWED: "bg-sky-100 text-sky-800 ring-sky-200",
  CORROBORATED: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  DISPUTED: "bg-amber-100 text-amber-800 ring-amber-200",
  REJECTED: "bg-red-100 text-red-800 ring-red-200",
  PROMOTED_TO_EVIDENCE: "bg-signal-100 text-signal-800 ring-signal-200",
};

const AUTHORITY_TONES: Record<string, string> = {
  OFFICIAL: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  PUBLIC_NEWS: "bg-sky-100 text-sky-800 ring-sky-200",
  PUBLIC_SOCIAL: "bg-ink-100 text-ink-600 ring-ink-200",
  ARCHIVAL: "bg-amber-100 text-amber-800 ring-amber-200",
  COMMERCIAL: "bg-violet-100 text-violet-800 ring-violet-200",
};

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Request failed";
}

export default function Osint() {
  const canRead = useCan("osint:read");
  const canCollect = useCan("osint:collect");
  const canAdmin = useCan("osint:admin");
  const canPromote = useCan("intelligence:create");

  const [recordId, setRecordId] = useState<string | null>(null);

  if (!canRead) {
    return (
      <div>
        <PageHeader
          eyebrow="OSINT gate"
          title="Open source"
          description="Open-source intelligence collection is not available to your role."
        />
        <EmptyState title="Access restricted" description="You need the osint:read permission to view the open-source registry." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="OSINT gate"
        title="Open source"
        description="Collect open-source intelligence from real Tier-1 sources. Provenance, source health and dedupe are stored with every record; content is only ever promoted to intelligence explicitly."
      />

      {canCollect ? <CollectPanel /> : (
        <Card>
          <CardBody>
            <p className="text-sm text-ink-500">Your role can review collected records but cannot trigger collection.</p>
          </CardBody>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,400px)_1fr]">
        <div className="space-y-6">
          <SourcesCard canCollect={canCollect} canAdmin={canAdmin} />
          <ConnectorTypesCard />
        </div>

        <div>
          {recordId ? (
            <RecordPanel recordId={recordId} onBack={() => setRecordId(null)} canAdmin={canAdmin} canPromote={canPromote} />
          ) : (
            <RecordsCard onSelect={setRecordId} />
          )}
        </div>
      </div>
    </div>
  );
}

function CollectPanel() {
  const [terms, setTerms] = useState("");
  const [days, setDays] = useState("3");
  const [summary, setSummary] = useState<OsintCollectSummary[] | null>(null);

  const targeted = useOsintCollectTargetedMutation({
    onSuccess: (res) => {
      const ok = res.results.filter((r) => r.ok).length;
      toastSuccess(`Collect finished — ${ok}/${res.results.length} sources ok.`);
      setSummary(res.results);
    },
    onError: (e) => toastError(errMsg(e)),
  });

  return (
    <Card>
      <CardHeader className="items-center justify-between gap-2">
        <CardTitle>Targeted collection</CardTitle>
        <Radar className="h-4 w-4 text-ink-400" />
      </CardHeader>
      <CardBody className="space-y-4">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (!terms.trim()) {
              toastError("Enter search terms first.");
              return;
            }
            setSummary(null);
            targeted.mutate({
              terms: terms.trim(),
              days: days ? Number(days) : null,
            });
          }}
        >
          <Field id="osint-terms" label="Search terms" description="Plain-language query, e.g. “anabolic steroids anti-doping summit”." className="min-w-64 flex-1">
            <Input id="osint-terms" value={terms} onChange={(e) => setTerms(e.target.value)} placeholder="e.g. athlete banned stimulant" />
          </Field>
          <Field id="osint-days" label="Since">
            <Select id="osint-days" value={days} onChange={(e) => setDays(e.target.value)} className="w-32">
              <option value="1">1 day</option>
              <option value="3">3 days</option>
              <option value="7">7 days</option>
              <option value="30">30 days</option>
              <option value="">Any</option>
            </Select>
          </Field>
          <Button type="submit" variant="secondary" loading={targeted.isPending} disabled={!terms.trim()}>
            {targeted.isPending ? "Collecting…" : "Run targeted collect"}
          </Button>
        </form>

        {summary ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {summary.map((r) => (
              <div key={r.source_id} className="rounded-md border border-ink-100 px-3 py-2 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate font-medium text-ink-900">{r.source_name}</p>
                  <HealthBadge>{r.health}</HealthBadge>
                </div>
                {r.ok ? (
                  <p className="mt-0.5 text-xs text-ink-600">
                    {r.new_records} new{r.duplicates > 0 ? ` · ${r.duplicates} dupes` : ""}{r.mentions > 0 ? ` · ${r.mentions} mentions` : ""}
                  </p>
                ) : (
                  <p className="mt-0.5 truncate text-xs text-red-700" title={r.error ?? ""}>{r.error}</p>
                )}
              </div>
            ))}
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

function SourcesCard({ canCollect, canAdmin }: { canCollect: boolean; canAdmin: boolean }) {
  const [showForm, setShowForm] = useState(false);
  const sources = useOsintSourcesQuery({ limit: 100, include_disabled: true });

  return (
    <Card>
      <CardHeader className="items-center justify-between gap-2">
        <CardTitle>Source registry</CardTitle>
        <div className="flex items-center gap-2">
          <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{sources.data?.count ?? 0} sources</Badge>
          {canAdmin ? (
            <Button variant="outline" size="sm" onClick={() => setShowForm((v) => !v)}>
              {showForm ? "Close" : "Register source"}
            </Button>
          ) : null}
        </div>
      </CardHeader>
      <CardBody className="p-0">
        {canAdmin && showForm ? <SourceForm /> : null}
        {sources.isLoading ? (
          <PageLoading label="Loading sources" />
        ) : sources.isError ? (
          <div className="p-4"><ErrorState title="Could not load sources" onRetry={() => void sources.refetch()} /></div>
        ) : sources.data && sources.data.sources.length === 0 ? (
          <div className="p-4">
            <EmptyState
              title="No sources registered"
              description={canAdmin ? "Register a source or seed the default public registry." : "An administrator must register sources first."}
              action={canAdmin ? <SeedDefaultsButton /> : undefined}
            />
          </div>
        ) : (
          <ul className="divide-y divide-ink-50">
            {sources.data?.sources.map((src) => (
              <SourceRow key={src.id} source={src} canCollect={canCollect} canAdmin={canAdmin} />
            ))}
          </ul>
        )}
        {sources.data && sources.data.sources.length > 0 && canAdmin ? (
          <div className="border-t border-ink-100 p-3">
            <SeedDefaultsButton />
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

function SeedDefaultsButton() {
  const seed = useOsintSeedDefaultsMutation({
    onSuccess: (res) => toastSuccess(`${res.sources_total} sources in registry.`),
    onError: (e) => toastError(errMsg(e)),
  });
  return (
    <Button variant="outline" size="sm" loading={seed.isPending} onClick={() => seed.mutate()}>
      {seed.isPending ? "Seeding…" : "Seed default sources"}
    </Button>
  );
}

function SourceForm() {
  const [body, setBody] = useState<OsintSourceCreateBody>({
    source_id: "",
    name: "",
    connector_type: "web_doc",
    url: "",
    authority: "PUBLIC_NEWS",
    jurisdiction: "",
    enabled: true,
    rate_limit_per_min: 30,
  });
  const connTypes = useOsintConnectorTypesQuery();

  const create = useOsintCreateSourceMutation({
    onSuccess: (src) => {
      toastSuccess(`Registered "${src.name}".`);
      setBody({ ...body, source_id: "", name: "", url: "" });
    },
    onError: (e) => toastError(errMsg(e)),
  });

  return (
    <form
      className="space-y-3 border-b border-ink-100 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate({ ...body, jurisdiction: body.jurisdiction ? body.jurisdiction : null });
      }}
    >
      <Field id="osint-src-id" label="Source ID" description="Unique slug used by supporting code, e.g. wada-public" required>
        <Input id="osint-src-id" value={body.source_id} onChange={(e) => setBody({ ...body, source_id: e.target.value })} placeholder="e.g. wada-public" required />
      </Field>
      <Field id="osint-src-name" label="Display name" required>
        <Input id="osint-src-name" value={body.name} onChange={(e) => setBody({ ...body, name: e.target.value })} placeholder="e.g. WADA public statements" required />
      </Field>
      <Field id="osint-src-type" label="Connector">
        <Select id="osint-src-type" value={body.connector_type} onChange={(e) => setBody({ ...body, connector_type: e.target.value })}>
          {connTypes.data?.connectors.map((c) => (
            <option key={c.connector_type} value={c.connector_type}>{c.connector_type}</option>
          )) ?? <option value="web_doc">web_doc</option>}
        </Select>
      </Field>
      <Field id="osint-src-url" label="URL" description="Only public, official endpoints are allowed." required>
        <Input id="osint-src-url" type="url" value={body.url} onChange={(e) => setBody({ ...body, url: e.target.value })} placeholder="https://www.wada-ama.org/en/rss.xml" required />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field id="osint-src-authority" label="Authority">
          <Select id="osint-src-authority" value={body.authority as string} onChange={(e) => setBody({ ...body, authority: e.target.value })}>
            {["OFFICIAL", "PUBLIC_NEWS", "PUBLIC_SOCIAL", "ARCHIVAL", "COMMERCIAL"].map((a) => (
              <option key={a} value={a}>{titleCase(a)}</option>
            ))}
          </Select>
        </Field>
        <Field id="osint-src-jurisdiction" label="Jurisdiction">
          <Input id="osint-src-jurisdiction" value={body.jurisdiction ?? ""} onChange={(e) => setBody({ ...body, jurisdiction: e.target.value })} placeholder="e.g. Global" />
        </Field>
      </div>
      <Button type="submit" variant="secondary" loading={create.isPending}>
        {create.isPending ? "Registering…" : "Register source"}
      </Button>
    </form>
  );
}

function SourceRow({ source, canCollect, canAdmin }: {
  source: NonNullable<ReturnType<typeof useOsintSourcesQuery>["data"]>["sources"][number];
  canCollect: boolean;
  canAdmin: boolean;
}) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const collect = useOsintCollectSourceMutation({
    onSuccess: (res) => {
      setBusyId(null);
      toastSuccess(res.ok
        ? `Collected ${res.new_records} new record${res.new_records === 1 ? "" : "s"} from ${res.source_name}.`
        : `${res.source_name}: ${res.error}`);
    },
    onError: (e) => {
      setBusyId(null);
      toastError(errMsg(e));
    },
  });
  const toggle = useOsintUpdateSourceMutation({
    onSuccess: (src) => toastSuccess(src.enabled ? `Enabled ${src.name}.` : `Disabled ${src.name}.`),
    onError: (e) => toastError(errMsg(e)),
  });
  const remove = useOsintDeleteSourceMutation({
    onSuccess: () => toastSuccess("Source removed."),
    onError: (e) => toastError(errMsg(e)),
  });

  const disabled = source.health === "DISABLED" || !source.enabled;

  return (
    <li className="px-4 py-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium text-ink-900">{source.name}</p>
            <HealthBadge>{source.health}</HealthBadge>
            {source.authority ? <AuthorityBadge>{source.authority}</AuthorityBadge> : null}
          </div>
          <p className="mt-0.5 truncate font-mono text-xs text-ink-500" title={source.url}>{source.source_id} · {source.url}</p>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-ink-500">
            <span>{source.connector_type}</span>
            {source.jurisdiction ? <><span aria-hidden>·</span><span>{source.jurisdiction}</span></> : null}
            {source.last_success_at ? <><span aria-hidden>·</span><span>OK {formatIso(source.last_success_at)}</span></> : null}
            {source.last_failure_at ? (
              <span className="text-red-700" title={source.last_failure_reason ?? ""}>
                · failed {formatIso(source.last_failure_at)}
              </span>
            ) : null}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {canCollect && !disabled ? (
            <Button
              variant="outline"
              size="sm"
              loading={busyId === source.id}
              onClick={() => {
                setBusyId(source.id);
                collect.mutate(
                  { sourceId: source.id },
                  { onSettled: () => setBusyId(null) },
                );
              }}
            >
              {busyId === source.id ? "Collecting…" : "Collect"}
            </Button>
          ) : null}
          {canAdmin ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => toggle.mutate({ sourceId: source.id, body: { enabled: !source.enabled } })}
              >
                {source.enabled ? "Disable" : "Enable"}
              </Button>
              <Button variant="ghost" size="icon" aria-label={`Remove ${source.name}`} onClick={() => remove.mutate(source.source_id)}>
                <Trash2 className="h-4 w-4 text-red-600" />
              </Button>
            </>
          ) : null}
        </div>
      </div>
    </li>
  );
}

function ConnectorTypesCard() {
  const conn = useOsintConnectorTypesQuery();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Connectors</CardTitle>
      </CardHeader>
      <CardBody className="p-0">
        {conn.isLoading ? (
          <PageLoading label="Loading connectors" />
        ) : conn.data && conn.data.connectors.length === 0 ? (
          <div className="p-4"><EmptyState title="No connectors" description="The OSINT subsystem is not provisioned." /></div>
        ) : (
          <ul className="divide-y divide-ink-50">
            {conn.data?.connectors.map((c) => (
              <li key={c.connector_type} className="flex items-center justify-between gap-2 px-4 py-2.5 text-sm">
                <span className="font-medium text-ink-900">{c.connector_type}</span>
                <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">
                  {c.search_driven ? "search" : c.source_kind ?? "pull"}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

function RecordsCard({ onSelect }: { onSelect: (id: string) => void }) {
  const [q, setQ] = useState("");
  const [authority, setAuthority] = useState("");
  const [includeDupes, setIncludeDupes] = useState(false);

  const records = useOsintRecordsQuery({
    q: q || undefined,
    authority: authority || undefined,
    include_duplicates: includeDupes,
    limit: 100,
  });

  return (
    <Card>
      <CardHeader className="items-center justify-between gap-2">
        <CardTitle>Collected records</CardTitle>
        <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{records.data?.count ?? 0} records</Badge>
      </CardHeader>
      <CardBody className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Input
            aria-label="Search records"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search title / publisher"
            className="h-8 w-full max-w-xs text-sm"
          />
          <Select aria-label="Authority filter" value={authority} onChange={(e) => setAuthority(e.target.value)} className="h-8 w-40 text-sm">
            <option value="">Any authority</option>
            {["OFFICIAL", "PUBLIC_NEWS", "PUBLIC_SOCIAL", "ARCHIVAL", "COMMERCIAL"].map((a) => (
              <option key={a} value={a}>{titleCase(a)}</option>
            ))}
          </Select>
          <label className="flex items-center gap-1.5 text-sm text-ink-800">
            <input type="checkbox" className="h-4 w-4" checked={includeDupes} onChange={(e) => setIncludeDupes(e.target.checked)} />
            Show duplicates
          </label>
        </div>

        {records.isLoading ? (
          <PageLoading label="Loading records" />
        ) : records.isError ? (
          <ErrorState title="Could not load records" onRetry={() => void records.refetch()} />
        ) : records.data && records.data.records.length === 0 ? (
          <EmptyState title="No records yet" description="Run a collection to populate the OSINT store." />
        ) : (
          <div className="max-h-[36rem] overflow-auto rounded-md border border-ink-100">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-paper-50">
                <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="py-2 pl-4 pr-3">Title / publisher</th>
                  <th className="py-2 pr-3">Source</th>
                  <th className="py-2 pr-3">Published</th>
                  <th className="py-2 pr-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-50">
                {records.data?.records.map((rec) => (
                  <RecordRow key={rec.id} rec={rec} onSelect={() => onSelect(rec.id)} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function RecordRow({ rec, onSelect }: { rec: OsintRecordItem; onSelect: () => void }) {
  return (
    <tr className="cursor-pointer hover:bg-ink-50" onClick={onSelect}>
      <td className="max-w-72 py-2 pl-4 pr-3">
        <p className="truncate font-medium text-ink-900" title={rec.title}>{rec.title}</p>
        <p className="truncate text-xs text-ink-500">{rec.publisher ?? rec.source}</p>
      </td>
      <td className="py-2 pr-3">
        <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{rec.source_type}</Badge>
      </td>
      <td className="py-2 pr-3 text-xs text-ink-600">{rec.published_at ? formatIso(rec.published_at) : "—"}</td>
      <td className="py-2 pr-4">
        {rec.is_duplicate ? (
          <Badge tone="warn">{rec.duplicate_reason === "SYNDICATION" ? "Syndicated" : "Duplicate"}</Badge>
        ) : rec.terms_matched ? (
          <Badge tone="success">Matched</Badge>
        ) : (
          <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">New</Badge>
        )}
      </td>
    </tr>
  );
}

function RecordPanel({ recordId, onBack, canAdmin, canPromote }: { recordId: string; onBack: () => void; canAdmin: boolean; canPromote: boolean }) {
  const detail = useOsintRecordDetailQuery(recordId);
  const [claimPredicate, setClaimPredicate] = useState("");
  const [claimObject, setClaimObject] = useState("");

  const createClaim = useOsintCreateClaimMutation({
    onSuccess: () => {
      toastSuccess("Claim created.");
      setClaimPredicate("");
      setClaimObject("");
      void detail.refetch();
    },
    onError: (e) => toastError(errMsg(e)),
  });
  const promote = useOsintPromoteMutation({
    onSuccess: (res) => {
      toastSuccess(`Promoted to intelligence report ${res.report_id.slice(0, 8)}.`);
      void detail.refetch();
    },
    onError: (e) => toastError(errMsg(e)),
  });
  const reviewClaim = useOsintReviewClaimMutation({
    onSuccess: (claim) => {
      toastSuccess(`Claim ${titleCase(claim.verification)}.`);
      void detail.refetch();
    },
    onError: (e) => toastError(errMsg(e)),
  });

  if (detail.isLoading) return <PageLoading label="Loading record" />;
  if (detail.isError || !detail.data) {
    return (
      <Card>
        <CardBody>
          <ErrorState title="Could not load record" onRetry={() => void detail.refetch()} />
          <Button variant="ghost" size="sm" className="mt-2" onClick={onBack}>Back to records</Button>
        </CardBody>
      </Card>
    );
  }

  const rec = detail.data;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="items-start justify-between gap-2">
          <div className="min-w-0">
            <CardTitle>{rec.title}</CardTitle>
            <p className="mt-0.5 text-xs text-ink-500">
              {rec.publisher ?? rec.source?.name ?? "—"}
              {rec.published_at ? ` · ${formatIso(rec.published_at)}` : ""}
              {" · "}{rec.source_type}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {rec.is_duplicate ? <Badge tone="warn">{rec.duplicate_reason === "SYNDICATION" ? "Syndicated copy" : "Duplicate"}</Badge> : null}
            <Button variant="ghost" size="sm" onClick={onBack}>Back to records</Button>
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs text-ink-500">Source URL</dt>
              <dd className="truncate font-mono text-xs text-ink-700" title={rec.canonical_url ?? rec.source_url ?? "—"}>
                {(rec.canonical_url ?? rec.source_url ?? "—").slice(0, 64)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-ink-500">Retrieved</dt>
              <dd className="font-medium text-ink-900">{formatIso(rec.retrieved_at)}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-500">Content hash</dt>
              <dd className="truncate font-mono text-xs text-ink-700" title={rec.content_hash ?? "—"}>{(rec.content_hash ?? "—").slice(0, 16)}</dd>
            </div>
            {rec.syndication_group ? (
              <div>
                <dt className="text-xs text-ink-500">Syndication group</dt>
                <dd className="truncate font-mono text-xs text-ink-700" title={rec.syndication_group}>{rec.syndication_group.slice(0, 16)}</dd>
              </div>
            ) : null}
            <div>
              <dt className="text-xs text-ink-500">Authority</dt>
              <dd><AuthorityBadge>{rec.authority_level}</AuthorityBadge></dd>
            </div>
            <div>
              <dt className="text-xs text-ink-500">Language</dt>
              <dd className="font-medium text-ink-900">{rec.language ?? "—"}</dd>
            </div>
          </dl>

          {rec.content ? (
            <div className="rounded-md border border-ink-100 bg-ink-50/40 p-3">
              <p className="max-h-40 overflow-auto whitespace-pre-wrap font-serif text-sm leading-relaxed text-ink-700">{rec.content}</p>
            </div>
          ) : null}

          {rec.mentions.length > 0 ? (
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-ink-500">Mentions</p>
              <ul className="flex flex-wrap gap-1.5">
                {rec.mentions.map((m) => (
                  <Badge key={m.id} tone="info">{m.subject_label} <span className="opacity-70">({m.subject_type})</span></Badge>
                ))}
              </ul>
            </div>
          ) : null}

          {canPromote ? (
            <Button
              variant="secondary"
              loading={promote.isPending}
              disabled={rec.promoted_reports > 0}
              onClick={() => promote.mutate({ recordId: rec.id })}
            >
              <ShieldCheck className="h-4 w-4" />
              {rec.promoted_reports > 0 ? `Promoted (${rec.promoted_reports})` : "Promote to intelligence"}
            </Button>
          ) : null}
        </CardBody>
      </Card>

      {canAdmin ? (
        <Card>
          <CardHeader>
            <CardTitle>Claims</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            {rec.claims.length > 0 ? (
              <ul className="space-y-2">
                {rec.claims.map((claim) => (
                  <li key={claim.id} className="rounded-md border border-ink-100 px-3 py-2">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm text-ink-900">
                        <span className="font-medium">{claim.predicate}</span>
                        <span className="text-ink-500"> → </span>
                        {claim.object_value}
                        {claim.subject_label ? <span className="text-ink-500"> ({claim.subject_label})</span> : null}
                      </p>
                      <Badge tone="neutral" className={cn("shrink-0", VERIFY_TONE[claim.verification])}>{titleCase(claim.verification)}</Badge>
                    </div>
                    {claim.notes ? <p className="mt-1 text-xs text-ink-500">{claim.notes}</p> : null}
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Select
                        className="h-8 w-40 text-xs"
                        aria-label={`Review ${claim.predicate}`}
                        value={claim.verification}
                        onChange={(e) => reviewClaim.mutate({ claimId: claim.id, body: { verification: e.target.value } })}
                      >
                        {["UNREVIEWED", "REVIEWED", "CORROBORATED", "DISPUTED", "REJECTED", "PROMOTED_TO_EVIDENCE"].map((v) => (
                          <option key={v} value={v}>{titleCase(v)}</option>
                        ))}
                      </Select>
                      {claim.confidence != null ? <span className="text-xs text-ink-500">confidence {claim.confidence}</span> : null}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-ink-500">No analyst claims recorded for this record yet.</p>
            )}

            <form
              className="space-y-3 border-t border-ink-100 pt-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!claimPredicate.trim() || !claimObject.trim()) {
                  toastError("Predicate and object are required.");
                  return;
                }
                createClaim.mutate({
                  recordId: rec.id,
                  body: {
                    predicate: claimPredicate.trim(),
                    object_value: claimObject.trim(),
                    subject_label: rec.mentions[0]?.subject_label ?? null,
                    subject_type: rec.mentions[0]?.subject_type ?? null,
                    subject_id: rec.mentions[0]?.subject_id ?? null,
                  },
                });
              }}
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <Field id="claim-predicate" label="Predicate" description="e.g. elected_to, sanctioned_by">
                  <Input id="claim-predicate" value={claimPredicate} onChange={(e) => setClaimPredicate(e.target.value)} placeholder="sanctioned_by" />
                </Field>
                <Field id="claim-object" label="Object">
                  <Input id="claim-object" value={claimObject} onChange={(e) => setClaimObject(e.target.value)} placeholder="ADRV for GW1516" />
                </Field>
              </div>
              <Button variant="outline" size="sm" type="submit" loading={createClaim.isPending}>
                {createClaim.isPending ? "Adding…" : "Add claim"}
              </Button>
            </form>
          </CardBody>
        </Card>
      ) : null}

      <DedupeCard recordId={rec.id} />
    </div>
  );
}

function DedupeCard({ recordId }: { recordId: string }) {
  const [open, setOpen] = useState(false);
  const cluster = useOsintDedupeClusterQuery(recordId, open);
  return (
    <Card>
      <CardHeader className="items-center justify-between gap-2">
        <CardTitle>Dedupe & syndication</CardTitle>
        <Button variant="ghost" size="sm" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide" : "View cluster"}
        </Button>
      </CardHeader>
      <CardBody className="p-0">
        {!open ? (
          <div className="p-4 text-sm text-ink-500">Expand to see how this record relates to other collected items.</div>
        ) : cluster.isLoading ? (
          <div className="p-4"><PageLoading label="Loading cluster" /></div>
        ) : cluster.isError || !cluster.data ? (
          <div className="p-4"><ErrorState title="Could not load cluster" onRetry={() => void cluster.refetch()} /></div>
        ) : (
          <div>
            <dl className="grid grid-cols-3 gap-x-6 gap-y-2 border-b border-ink-100 px-4 py-3 text-sm">
              <div>
                <dt className="text-xs text-ink-500">Copies</dt>
                <dd className="font-medium text-ink-900">{cluster.data.member_count}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-500">Independent sources</dt>
                <dd className="font-medium text-ink-900">{cluster.data.independent_sources}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-500">Publishers</dt>
                <dd className="truncate font-medium text-ink-900" title={cluster.data.publishers.join(", ")}>
                  {cluster.data.publishers.join(", ") || "—"}
                </dd>
              </div>
            </dl>
            <ul className="divide-y divide-ink-50">
              {cluster.data.members.map((m) => (
                <li key={m.id} className="flex items-center justify-between gap-2 px-4 py-2 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-ink-900" title={m.title}>{m.title}</p>
                    <p className="truncate text-xs text-ink-500">{m.publisher ?? m.source}</p>
                  </div>
                  {m.id === recordId ? (
                    <Badge tone="info">This record</Badge>
                  ) : m.is_duplicate ? (
                    <Badge tone="warn">Copy</Badge>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function HealthBadge({ children }: { children: string }) {
  return (
    <Badge tone="neutral" className={cn("shrink-0", HEALTH_TONE[children] ?? "bg-ink-100 text-ink-700 ring-ink-200")}>
      <RefreshCw className="h-3 w-3" aria-hidden={false} />
      {titleCase(children)}
    </Badge>
  );
}

function AuthorityBadge({ children }: { children: string }) {
  return (
    <Badge tone="neutral" className={cn("shrink-0", AUTHORITY_TONES[children] ?? "bg-ink-100 text-ink-700 ring-ink-200")}>
      {titleCase(children)}
    </Badge>
  );
}