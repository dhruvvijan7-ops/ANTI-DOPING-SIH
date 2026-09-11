import { Network } from "lucide-react";
import type { NodeDetail } from "@/lib/api/types";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface Props {
  entityType: string;
  entityId: string;
  detail: NodeDetail | undefined;
  onClose: () => void;
}

export function NodeDetailPanel({ entityType: _entityType, entityId, detail, onClose }: Props) {
  return (
    <Card className="w-80 shrink-0 max-h-[480px] overflow-y-auto">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Entity Detail</CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>✕</Button>
        </div>
      </CardHeader>
      <CardBody className="space-y-3">
        {detail ? (
          <>
            <div className="flex items-center gap-2">
              <Network className="h-4 w-4 text-ink-500" />
              <span className="text-sm font-semibold text-ink-900">{detail.name}</span>
            </div>
            <div className="space-y-1 text-xs text-ink-600">
              <p>Type: <Badge>{detail.entity_type}</Badge></p>
              {detail.graph_role ? <p>Role: <Badge>{detail.graph_role}</Badge></p> : null}
              {detail.verification ? <p>Verification: <Badge>{detail.verification}</Badge></p> : null}
              <p>Connections: {detail.degree}</p>
              <p>Intelligence reports: {detail.intel_count}</p>
              <p>Investigations: {detail.investigation_count}</p>
            </div>
            {detail.relationships.length > 0 ? (
              <div>
                <p className="mb-1 text-xs font-medium text-ink-700">Related entities</p>
                <ul className="space-y-1">
                  {detail.relationships.map((r) => (
                    <li key={r.id} className="flex items-center justify-between rounded bg-ink-50 px-2 py-1 text-[10px]">
                      <span className="truncate text-ink-700">{r.other_name ?? r.other_entity_type}</span>
                      <Badge>{r.relationship_type}</Badge>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <p className="text-[10px] text-ink-400">ID: {entityId}</p>
          </>
        ) : (
          <p className="py-4 text-center text-xs text-ink-500">Loading…</p>
        )}
      </CardBody>
    </Card>
  );
}
