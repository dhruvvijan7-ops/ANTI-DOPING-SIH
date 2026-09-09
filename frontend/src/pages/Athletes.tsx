import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAthletesQuery } from "@/lib/api/queries";
import type { AthleteSummary } from "@/lib/api/types";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { Input } from "@/components/ui/field";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, User } from "lucide-react";

export default function Athletes() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const list = useAthletesQuery({ q: q || undefined, limit: 250 });

  const athletes = list.data?.athletes ?? [];
  const sorted = [...athletes].sort((a, b) => a.full_name.localeCompare(b.full_name));

  return (
    <div>
      <PageHeader
        eyebrow="Registered participants"
        title="Athletes"
        description="Profiles maintained for testing, whereabouts, competition and intelligence correlation."
      />

      <div className="mb-4">
        <label className="sr-only" htmlFor="athlete-search">Filter athletes</label>
        <Input
          id="athlete-search"
          placeholder="Search by name or reference…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-md"
        />
      </div>

      <Card>
        <CardBody>
          {list.isLoading ? <PageLoading label="Loading athletes" /> : list.isError ? (
            <ErrorState title="Could not load athletes" onRetry={() => void list.refetch()} />
          ) : sorted.length === 0 ? (
            <EmptyState icon={<User className="h-6 w-6" />} title="No athletes found" description="Try adjusting the search filter." />
          ) : (
            <ul className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
              {sorted.map((a) => (
                <AthleteRow key={a.id} athlete={a} onOpen={() => navigate(`/athletes/${a.id}`)} />
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function AthleteRow({ athlete, onOpen }: { athlete: AthleteSummary; onOpen: () => void }) {
  return (
    <li>
      <button
        onClick={onOpen}
        className="flex w-full items-center justify-between gap-3 rounded-md border border-ink-100 px-3 py-3 text-left transition-colors hover:border-signal-300 hover:bg-signal-50/40"
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium text-ink-900">{athlete.full_name}</p>
            <Badge tone="neutral" className="bg-ink-100 text-ink-500 ring-ink-200">{athlete.external_ref}</Badge>
          </div>
          <p className="mt-1 text-xs text-ink-500">
            {athlete.sport}{athlete.discipline ? ` · ${athlete.discipline}` : ""} · {athlete.nationality}
          </p>
        </div>
        <ArrowRight className="h-4 w-4 shrink-0 text-ink-300" />
      </button>
    </li>
  );
}