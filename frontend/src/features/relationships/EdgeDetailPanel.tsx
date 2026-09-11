import { Link } from "lucide-react";
import type { RelationshipDetail } from "@/lib/api/types";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useCan } from "@/stores/auth";
import { useDeleteRelationshipMutation } from "@/lib/api/queries";
import { toastSuccess, toastError } from "@/components/ui/toasts";

interface Props {
  detail: RelationshipDetail | undefined;
  onClose: () => void;
}

export function EdgeDetailPanel({ detail, onClose }: Props) {
  const canModify = useCan("investigations:modify");
  const deleteMut = useDeleteRelationshipMutation({
    onSuccess: () => {
      toastSuccess("Relationship deleted.");
      onClose();
    },
    onError: (e) => {
      toastError(e instanceof Error ? e.message : "Delete failed");
    },
  });

  const confidencePercent = detail ? Math.round((detail.confidence ?? 0) * 100) : 0;

  return (
    <Card className="w-80 shrink-0 max-h-[480px] overflow-y-auto">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Relationship Detail</CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>✕</Button>
        </div>
      </CardHeader>
      <CardBody className="space-y-3">
        {detail ? (
          <>
            <div className="flex items-center gap-2">
              <Link className="h-4 w-4 text-ink-500" />
              <span className="text-sm font-semibold text-ink-900">{detail.relationship_type}</span>
            </div>
            <div className="space-y-1 text-xs text-ink-600">
              <p>From: <span className="font-medium">{detail.from_name ?? detail.from_entity_type}</span> <Badge>{detail.from_entity_type}</Badge></p>
              <p>To: <span className="font-medium">{detail.to_name ?? detail.to_entity_type}</span> <Badge>{detail.to_entity_type}</Badge></p>
              <p>Confidence: <span className="font-medium">{confidencePercent}%</span></p>
              {detail.frequency ? <p>Frequency: {detail.frequency}</p> : null}
              {detail.verification ? <p>Verification: <Badge>{detail.verification}</Badge></p> : null}
              {detail.start_date ? <p>Start: {detail.start_date}</p> : null}
              {detail.end_date ? <p>End: {detail.end_date}</p> : null}
            </div>
            {detail.notes ? (
              <div>
                <p className="mb-0.5 text-xs font-medium text-ink-700">Notes</p>
                <p className="text-xs text-ink-600">{detail.notes}</p>
              </div>
            ) : null}
            {detail.provenance ? (
              <div className="rounded bg-ink-50 p-2 text-[10px] text-ink-500">
                {detail.provenance.source ? <p>Source: {detail.provenance.source.name}</p> : null}
                {detail.provenance.created_by_actor ? <p>Created by: {detail.provenance.created_by_actor.name}</p> : null}
                {detail.provenance.created_at ? <p>Created: {new Date(detail.provenance.created_at).toLocaleDateString()}</p> : null}
              </div>
            ) : null}
            {detail.related_intel.count > 0 ? (
              <div>
                <p className="mb-0.5 text-xs font-medium text-ink-700">Related intelligence ({detail.related_intel.count})</p>
                <ul className="space-y-0.5">
                  {detail.related_intel.titles.map((t, i) => (
                    <li key={i} className="truncate text-[10px] text-ink-500">{t}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {canModify && !detail.deleted ? (
              <Button
                variant="outline"
                size="sm"
                className="mt-2 text-red-600 hover:bg-red-50"
                onClick={() => {
                  if (detail.id && window.confirm("Soft-delete this relationship?")) {
                    deleteMut.mutate(detail.id);
                  }
                }}
              >
                Delete relationship
              </Button>
            ) : null}
            {detail.deleted ? <Badge>DELETED</Badge> : null}
          </>
        ) : (
          <p className="py-4 text-center text-xs text-ink-500">Loading…</p>
        )}
      </CardBody>
    </Card>
  );
}
