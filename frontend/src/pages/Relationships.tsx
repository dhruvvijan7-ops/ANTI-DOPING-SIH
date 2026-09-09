import { useRelationshipsQuery } from "@/lib/api/queries";
import { timeAgo } from "@/lib/utils";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState, ErrorState, PageLoading } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";

export default function Relationships() {
  const { data, isLoading, isError, refetch } = useRelationshipsQuery({ limit: 200 });

  return (
    <div>
      <PageHeader
        eyebrow="Entity links"
        title="Relationships"
        description="Known connections between athletes, support persons and organisations assembled from registered data, with a confidence level for each link."
      />

      <Card>
        <CardBody>
          {isLoading ? (
            <PageLoading label="Loading relationships" />
          ) : isError ? (
            <ErrorState title="Could not load relationships" onRetry={() => void refetch()} />
          ) : !data || data.relationships.length === 0 ? (
            <EmptyState title="No relationships registered" />
          ) : (
            <ul className="divide-y divide-ink-50">
              {data.relationships.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-ink-900">
                      {r.from_name} <span className="text-ink-400">↔</span> {r.to_name}
                    </p>
                    <p className="mt-0.5 text-xs text-ink-500">
                      {r.relationship_type.replaceAll("_", " ")} · recorded {r.start_date ? `since ${r.start_date}` : "date unknown"} · {timeAgo(r.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge tone="neutral" className="bg-ink-100 text-ink-700 ring-ink-200">
                      Confidence {(r.confidence * 100).toFixed(0)}%
                    </Badge>
                    <Badge tone={r.status === "ACTIVE" ? "success" : "neutral"}>{r.status.replaceAll("_", " ")}</Badge>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}