import { useInvestigationRelationshipsQuery } from "@/lib/api/queries";
import { RelationshipGraphView } from "@/features/relationships/RelationshipGraph";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/states";

export function InvRelationships({ id }: { id: string }) {
  const { data, isLoading, isError, refetch } = useInvestigationRelationshipsQuery(id);

  if (isLoading) return <p className="py-10 text-center text-sm text-ink-500">Mapping relationships…</p>;
  if (isError || !data) return <ErrorState title="Could not load the relationship map" onRetry={() => void refetch()} />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Relationship map</CardTitle>
        <span className="text-xs text-ink-500">{data.node_count} nodes · {data.edge_count} connections</span>
      </CardHeader>
      <CardBody>
        <RelationshipGraphView graph={data} />
        {data.note ? <p className="mt-2 text-xs text-ink-500">{data.note}</p> : null}
        {data.edges.length === 0 ? <p className="py-6 text-center text-sm text-ink-500">No connections found for this case.</p> : null}
      </CardBody>
    </Card>
  );
}