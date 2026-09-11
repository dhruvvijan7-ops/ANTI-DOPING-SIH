import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileSearch, X } from "lucide-react";
import { formatDate, timeAgo } from "@/lib/utils";
import { LIST_LIMIT, infoCategoryLabel, reliabilityLabel } from "@/lib/constants";
import { ApiError } from "@/lib/api/client";
import { useIntelDetailQuery, useIntelligenceQuery } from "@/lib/api/queries";
import type { IntelListItem } from "@/lib/api/types";
import { PageHeader } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { Input } from "@/components/ui/field";

export default function Intelligence() {
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<IntelListItem | null>(null);
  const navigate = useNavigate();

  const list = useIntelligenceQuery({ limit: LIST_LIMIT, q: q || undefined });
  const detail = useIntelDetailQuery(selected?.id);

  const reports = list.data?.reports ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Source material"
        title="Intelligence"
        description="Corroborated reports, observations and disclosures gathered from verified sources about athletes and support persons."
      />

      <Card>
        <CardBody>
          <div className="mb-4">
            <label className="sr-only" htmlFor="intel-search">Filter intelligence reports</label>
            <Input
              id="intel-search"
              placeholder="Filter by title, source or subject…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setSelected(null);
              }}
            />
          </div>

          {list.isError ? (
            <ErrorState
              title="Could not load intelligence"
              message={list.error instanceof ApiError ? list.error.message : undefined}
              onRetry={() => void list.refetch()}
            />
          ) : list.isLoading ? (
            <PageLoading label="Loading intelligence" />
          ) : reports.length === 0 ? (
            <EmptyState
              icon={<FileSearch className="h-6 w-6" />}
              title="No intelligence reports"
              description="Reports ingested from field sources appear here once they are classified and added."
            />
          ) : (
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
              <ul className="divide-y divide-ink-50">
                {reports.map((report) => (
                  <li key={report.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(report)}
                      className={`w-full rounded-md px-2 py-3 text-left transition-colors hover:bg-ink-50 ${
                        selected?.id === report.id ? "bg-ink-50" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-ink-900">{report.title}</p>
                          <p className="mt-1 line-clamp-2 text-xs text-ink-600">
                            {report.description ?? "No description recorded."}
                          </p>
                        </div>
                        <span className="shrink-0 text-xs text-ink-400">{timeAgo(report.ingestion_date)}</span>
                      </div>
                      <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
                        <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">
                          {infoCategoryLabel(report.info_category)}
                        </Badge>
                        <span className="text-ink-400">Reliability {reliabilityLabel(report.reliability)}</span>
                        <span className="text-ink-400">· {report.report_date ? formatDate(report.report_date) : "—"}</span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>

              <aside className="lg:sticky lg:top-24 lg:self-start">
                {detail.data ? (
                  <Card>
                    <CardBody>
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-xs font-medium uppercase tracking-wide text-ink-500">Report detail</p>
                          <h2 className="mt-1 text-base font-semibold text-ink-950">{detail.data.title}</h2>
                        </div>
                        <button
                          className="rounded-md p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-700"
                          onClick={() => setSelected(null)}
                          aria-label="Close detail"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>

                      <dl className="mt-4 space-y-3 text-sm">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <dt className="text-xs text-ink-500">Subject</dt>
                            <dd className="font-medium text-ink-900">{detail.data.subject_name}</dd>
                          </div>
                          <div>
                            <dt className="text-xs text-ink-500">Report date</dt>
                            <dd className="font-medium text-ink-900">{formatDate(detail.data.report_date)}</dd>
                          </div>
                        </div>
                        <div>
                          <dt className="text-xs text-ink-500">Category</dt>
                          <dd>{infoCategoryLabel(detail.data.info_category)}</dd>
                        </div>
                        <div>
                          <dt className="text-xs text-ink-500">Source</dt>
                          <dd className="font-medium text-ink-900">{detail.data.source?.name ?? "—"}</dd>
                        </div>
                        <div>
                          <dt className="text-xs text-ink-500">Reliability / Quality</dt>
                          <dd>
                            {reliabilityLabel(detail.data.reliability)} / {detail.data.information_quality}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs text-ink-500">Confidentiality</dt>
                          <dd>{detail.data.confidentiality}</dd>
                        </div>
                      </dl>

                      {detail.data.description ? (
                        <p className="mt-4 rounded-md border border-ink-100 bg-ink-50/60 p-3 text-sm leading-relaxed text-ink-800">
                          {detail.data.description}
                        </p>
                      ) : null}

                      <div className="mt-4 flex flex-wrap gap-1.5">
                        <Badge tone={detail.data.status === "CLOSED" ? "neutral" : "info"}>
                          {detail.data.status === "OPEN" ? "Open lead" : detail.data.status}
                        </Badge>
                        {detail.data.is_duplicate ? <Badge tone="warn">Duplicate indicator</Badge> : null}
                      </div>

                      {detail.data.subject_id ? (
                        <button
                          className="mt-4 inline-flex h-8 items-center rounded-md px-3 text-sm font-medium text-signal-700 ring-1 ring-inset ring-signal-200 hover:bg-signal-50"
                          onClick={() =>
                            navigate(detail.data.subject_type === "ATHLETE" ? `/athletes/${detail.data.subject_id}` : `/relationships?entity=SUPPORT_PERSON&id=${detail.data.subject_id}`)
                          }
                        >
                          Open subject profile
                        </button>
                      ) : null}
                    </CardBody>
                  </Card>
                ) : (
                  <Card>
                    <CardBody className="text-center">
                      <p className="text-sm font-medium text-ink-800">Select a report</p>
                      <p className="mt-1 text-xs text-ink-500">Details, source and reliability assessment appear here.</p>
                    </CardBody>
                  </Card>
                )}
              </aside>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}