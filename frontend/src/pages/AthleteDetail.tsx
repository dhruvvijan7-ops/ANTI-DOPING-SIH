import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import {
  useAthleteAbpQuery,
  useAthleteDetailQuery,
  useAthleteEventsQuery,
  useAthleteIntelQuery,
  useAthleteRelationshipsQuery,
  useAthleteTestsQuery,
  useAthleteTravelQuery,
  useAthleteWhereaboutsQuery,
} from "@/lib/api/queries";
import { formatDate, formatScore, titleCase } from "@/lib/utils";
import { infoCategoryLabel } from "@/lib/constants";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { Tabs, type TabItem } from "@/components/ui/tabs";
import { useState } from "react";

type TabKey = "overview" | "tests" | "abp" | "whereabouts" | "travel" | "events" | "intel" | "relationships";

export default function AthleteDetail() {
  const { athleteId } = useParams();
  const [tab, setTab] = useState<TabKey>("overview");

  const athlete = useAthleteDetailQuery(athleteId);
  const tests = useAthleteTestsQuery(athleteId);
  const abp = useAthleteAbpQuery(athleteId);
  const whereabouts = useAthleteWhereaboutsQuery(athleteId);
  const travel = useAthleteTravelQuery(athleteId);
  const events = useAthleteEventsQuery(athleteId);
  const intel = useAthleteIntelQuery(athleteId);
  const relationships = useAthleteRelationshipsQuery(athleteId);

  const tabs: Array<TabItem<TabKey>> = [
    { key: "overview", label: "Overview" },
    { key: "tests", label: "Test history", count: tests.data?.count },
    { key: "abp", label: "ABP", count: abp.data?.count },
    { key: "whereabouts", label: "Whereabouts", count: whereabouts.data?.count },
    { key: "travel", label: "Travel", count: travel.data?.count },
    { key: "events", label: "Events", count: events.data?.count },
    { key: "intel", label: "Intelligence", count: intel.data?.count },
    { key: "relationships", label: "Relationships", count: relationships.data?.count },
  ];

  if (athlete.isLoading) return <PageLoading label="Loading athlete profile" />;
  if (athlete.isError || !athlete.data)
    return <ErrorState title="Could not load this athlete" message="The profile may be restricted or unavailable." onRetry={() => void athlete.refetch()} />;

  const a = athlete.data;

  return (
    <div>
      <Link to="/athletes" className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink-600 hover:text-ink-900">
        <ArrowLeft className="h-4 w-4" /> All athletes
      </Link>
      <PageHeader
        eyebrow={a.external_ref}
        title={a.full_name}
        description={`${titleCase(a.sport)}${a.discipline ? ` · ${titleCase(a.discipline)}` : ""} · ${a.nationality}`}
      />

      <Tabs tabs={tabs} value={tab} onChange={setTab} className="mb-6" />

      {tab === "overview" ? <OverviewTab born={a.date_of_birth} team={a.team?.name ?? null} gender={a.gender} status={a.status} /> : null}
      {tab === "tests" ? <TestsTab loading={tests.isLoading} error={tests.isError} refetch={() => void tests.refetch()} items={tests.data?.tests ?? []} /> : null}
      {tab === "abp" ? <AbpTab loading={abp.isLoading} error={abp.isError} refetch={() => void abp.refetch()} items={abp.data?.observations ?? []} /> : null}
      {tab === "whereabouts" ? <WhereaboutsTab loading={whereabouts.isLoading} error={whereabouts.isError} refetch={() => void whereabouts.refetch()} items={whereabouts.data?.whereabouts ?? []} /> : null}
      {tab === "travel" ? <TravelTab loading={travel.isLoading} error={travel.isError} refetch={() => void travel.refetch()} items={travel.data?.travel ?? []} /> : null}
      {tab === "events" ? <EventsTab loading={events.isLoading} error={events.isError} refetch={() => void events.refetch()} items={events.data?.timeline ?? []} /> : null}
      {tab === "intel" ? <IntelTab loading={intel.isLoading} error={intel.isError} refetch={() => void intel.refetch()} items={intel.data?.reports ?? []} /> : null}
      {tab === "relationships" ? <RelationshipsTab loading={relationships.isLoading} error={relationships.isError} refetch={() => void relationships.refetch()} items={relationships.data?.relationships ?? []} /> : null}
    </div>
  );
}

function OverviewTab({ born, team, gender, status }: { born: string; team: string | null; gender: string; status: string }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MiniStat label="Date of birth" value={formatDate(born)} />
      <MiniStat label="Gender" value={titleCase(gender)} />
      <MiniStat label="Team / entity" value={team ?? "—"} />
      <MiniStat label="Status" value={titleCase(status)} />
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardBody>
        <p className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</p>
        <p className="mt-1 truncate text-sm font-semibold text-ink-950">{value}</p>
      </CardBody>
    </Card>
  );
}

function NotFoundBox({ loading, error, refetch }: { loading: boolean; error: boolean; refetch: () => void }) {
  if (loading) return <PageLoading />;
  if (error) return <ErrorState title="Could not load this section" onRetry={refetch} />;
  return null;
}

function TableCard({ children }: { children: React.ReactNode }) {
  return (
    <Card>
      <CardBody className="overflow-x-auto">{children}</CardBody>
    </Card>
  );
}

function TestsTab({ loading, error, refetch, items }: { loading: boolean; error: boolean; refetch: () => void; items: import("@/lib/api/types").TestRecord[] }) {
  return (
    <div>
      <NotFoundBox loading={loading} error={error} refetch={refetch} />
      {items.length === 0 && !loading && !error ? <EmptyState title="No test records" /> : (
        <TableCard>
          <table className="w-full text-sm">
            <thead><tr className="border-b border-ink-100 text-left text-xs uppercase text-ink-500"><th className="py-2 pr-3">Date</th><th className="py-2 pr-3">Type</th><th className="py-2 pr-3">Location</th><th className="py-2 pr-3">Result</th><th className="py-2">Laboratory ref</th></tr></thead>
            <tbody className="divide-y divide-ink-50">
              {items.map((t) => (
                <tr key={t.id}>
                  <td className="py-2 pr-3">{formatDate(t.test_date)}</td>
                  <td className="py-2 pr-3">{titleCase(t.test_type)}</td>
                  <td className="py-2 pr-3">{t.location}</td>
                  <td className="py-2 pr-3"><ResultChip classification={t.result_classification} /></td>
                  <td className="py-2 font-mono text-xs">{t.laboratory_ref ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      )}
    </div>
  );
}

function ResultChip({ classification }: { classification: string }) {
  const positive = classification.toUpperCase().includes("POSITIVE") || classification.toUpperCase().includes("ATYPICAL");
  return <Badge tone={positive ? "danger" : classification.toUpperCase() === "NEGATIVE" ? "success" : "neutral"}>{titleCase(classification)}</Badge>;
}

function AbpTab({ loading, error, refetch, items }: { loading: boolean; error: boolean; refetch: () => void; items: import("@/lib/api/types").BiologicalObservation[] }) {
  return (
    <div>
      <NotFoundBox loading={loading} error={error} refetch={refetch} />
      {items.length === 0 && !loading && !error ? <EmptyState title="No biological passport observations" /> : (
        <TableCard>
          <table className="w-full text-sm">
            <thead><tr className="border-b border-ink-100 text-left text-xs uppercase text-ink-500"><th className="py-2 pr-3">Date</th><th className="py-2 pr-3">Marker</th><th className="py-2 pr-3">Value</th><th className="py-2 pr-3">Unit</th><th className="py-2">Baseline deviation</th></tr></thead>
            <tbody className="divide-y divide-ink-50">
              {items.map((o) => (
                <tr key={o.id}>
                  <td className="py-2 pr-3">{formatDate(o.observation_date)}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{o.marker}</td>
                  <td className="py-2 pr-3 tabular-nums">{o.value}</td>
                  <td className="py-2 pr-3">{o.unit}</td>
                  <td className="py-2 tabular-nums">{formatScore(o.baseline_deviation)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      )}
    </div>
  );
}

function WhereaboutsTab({ loading, error, refetch, items }: { loading: boolean; error: boolean; refetch: () => void; items: import("@/lib/api/types").WhereaboutEvent[] }) {
  return (
    <div>
      <NotFoundBox loading={loading} error={error} refetch={refetch} />
      {items.length === 0 && !loading && !error ? <EmptyState title="No whereabouts records" /> : (
        <TableCard>
          <table className="w-full text-sm">
            <thead><tr className="border-b border-ink-100 text-left text-xs uppercase text-ink-500"><th className="py-2 pr-3">Date</th><th className="py-2 pr-3">Type</th><th className="py-2 pr-3">Expected</th><th className="py-2 pr-3">Observed</th><th className="py-2">Status</th></tr></thead>
            <tbody className="divide-y divide-ink-50">
              {items.map((w) => (
                <tr key={w.id}>
                  <td className="py-2 pr-3">{formatDate(w.event_date)}</td>
                  <td className="py-2 pr-3">{titleCase(w.event_type)}</td>
                  <td className="py-2 pr-3">{w.expected_location}</td>
                  <td className="py-2 pr-3">{w.observed_location ?? "—"}</td>
                  <td className="py-2"><Badge tone={w.status.toUpperCase() === "MISSED" ? "danger" : "success"}>{titleCase(w.status)}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      )}
    </div>
  );
}

function TravelTab({ loading, error, refetch, items }: { loading: boolean; error: boolean; refetch: () => void; items: import("@/lib/api/types").TravelEvent[] }) {
  return (
    <div>
      <NotFoundBox loading={loading} error={error} refetch={refetch} />
      {items.length === 0 && !loading && !error ? <EmptyState title="No travel records" /> : (
        <TableCard>
          <table className="w-full text-sm">
            <thead><tr className="border-b border-ink-100 text-left text-xs uppercase text-ink-500"><th className="py-2 pr-3">Date</th><th className="py-2 pr-3">Origin</th><th className="py-2 pr-3">Destination</th><th className="py-2">Type</th></tr></thead>
            <tbody className="divide-y divide-ink-50">
              {items.map((t) => (
                <tr key={t.id}>
                  <td className="py-2 pr-3">{formatDate(t.event_date)}</td>
                  <td className="py-2 pr-3">{t.origin}</td>
                  <td className="py-2 pr-3">{t.destination}</td>
                  <td className="py-2">{titleCase(t.event_type)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      )}
    </div>
  );
}

function EventsTab({ loading, error, refetch, items }: { loading: boolean; error: boolean; refetch: () => void; items: import("@/lib/api/types").TimelineMarker[] }) {
  return (
    <div>
      <NotFoundBox loading={loading} error={error} refetch={refetch} />
      {items.length === 0 && !loading && !error ? <EmptyState title="No milestone events" /> : (
        <Card>
          <CardBody>
            <ol className="relative border-l border-ink-100 pl-5">
              {items.map((e) => (
                <li key={e.id} className="pb-4 last:pb-0">
                  <span className="absolute -left-[5px] mt-1 h-2 w-2 rounded-full bg-signal-600" aria-hidden />
                  <p className="text-sm font-medium text-ink-900">{e.label}</p>
                  <p className="text-xs text-ink-500">{formatDate(e.date)} · {titleCase(e.kind)}</p>
                </li>
              ))}
            </ol>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function IntelTab({ loading, error, refetch, items }: { loading: boolean; error: boolean; refetch: () => void; items: import("@/lib/api/types").AthleteIntelItem[] }) {
  return (
    <div>
      <NotFoundBox loading={loading} error={error} refetch={refetch} />
      {items.length === 0 && !loading && !error ? <EmptyState title="No intelligence linked" /> : (
        <Card>
          <CardBody>
            <ul className="divide-y divide-ink-50">
              {items.map((r) => (
                <li key={r.id} className="py-2.5">
                  <p className="text-sm font-medium text-ink-900">{r.title}</p>
                  <p className="mt-0.5 text-xs text-ink-500">
                    {infoCategoryLabel(r.info_category)} · reliability {r.reliability} · {formatDate(r.report_date)}
                  </p>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function RelationshipsTab({ loading, error, refetch, items }: { loading: boolean; error: boolean; refetch: () => void; items: import("@/lib/api/types").RelationshipItem[] }) {
  return (
    <div>
      <NotFoundBox loading={loading} error={error} refetch={refetch} />
      {items.length === 0 && !loading && !error ? (
        <EmptyState title="No relationships mapped" description="Connections to support persons, teams and other entities appear here." />
      ) : (
        <Card>
          <CardBody>
            <ul className="divide-y divide-ink-50">
              {items.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-ink-900">
                      {r.from_name} <span className="text-ink-400">↔</span> {r.to_name}
                    </p>
                    <p className="mt-0.5 text-xs text-ink-500">
                      {r.relationship_type.replaceAll("_", " ")} · confidence {(r.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                  <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">{r.status}</Badge>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}
    </div>
  );
}