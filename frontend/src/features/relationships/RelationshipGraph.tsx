import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  type EdgeTypes,
  type OnNodeDrag,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { RelationshipGraph as Graph } from "@/lib/api/types";
import { useUpdateNodePositionMutation, useNodeDetailQuery, useRelationshipDetailQuery } from "@/lib/api/queries";
import { EntityNode } from "./EntityNode";
import { RelationshipEdge } from "./RelationshipEdge";
import { NodeDetailPanel } from "./NodeDetailPanel";
import { EdgeDetailPanel } from "./EdgeDetailPanel";

const NODE_COLORS: Record<string, string> = {
  ATHLETE: "#14243a",
  SUPPORT_PERSON: "#0e7490",
  TEAM: "#0f766e",
  ORGANIZATION: "#7c2d12",
  PROVIDER: "#6b21a8",
  SUPPLEMENT: "#a16207",
  EVENT: "#b91c1c",
  COMPETITION: "#dc2626",
  LOCATION: "#15803d",
  SOURCE: "#4338ca",
  default: "#64748b",
};

export function RelationshipGraphView({ graph }: { graph: Graph }) {
  const updatePosition = useUpdateNodePositionMutation();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedNodeType, setSelectedNodeType] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  const { data: nodeDetail } = useNodeDetailQuery(selectedNodeType ?? undefined, selectedNodeId ?? undefined);
  const { data: edgeDetail } = useRelationshipDetailQuery(selectedEdgeId ?? undefined);

  const initialNodes: Node[] = useMemo(
    () =>
      graph.nodes.map((n) => ({
        id: `${n.kind}:${n.id}`,
        position: { x: 0, y: 0 },
        data: {
          label: n.label,
          kind: n.kind,
          entityId: n.id,
          isSubject: n.is_subject,
          color: NODE_COLORS[n.kind] ?? NODE_COLORS.default,
        },
        type: "entityNode",
      })),
    [graph]
  );

  const initialEdges: Edge[] = useMemo(
    () =>
      graph.edges.map((e) => ({
        id: e.id,
        source: `${graph.nodes.find((n) => n.id === e.source)?.kind ?? "UNKNOWN"}:${e.source}`,
        target: `${graph.nodes.find((n) => n.id === e.target)?.kind ?? "UNKNOWN"}:${e.target}`,
        label: e.label.replaceAll("_", " "),
        data: {
          confidence: e.data.confidence,
          relationshipType: e.data.relationship_type,
          relationshipId: e.data.relationship_id,
          startDate: e.data.start_date,
          endDate: e.data.end_date,
        },
        type: "relationshipEdge",
        animated: e.data.confidence < 0.5,
      })),
    [graph]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const nodeTypes: NodeTypes = useMemo(() => ({ entityNode: EntityNode }), []);
  const edgeTypes: EdgeTypes = useMemo(() => ({ relationshipEdge: RelationshipEdge }), []);

  const onNodeDragStop: OnNodeDrag = useCallback(
    (_, node) => {
      const [entityType, ...idParts] = node.id.split(":");
      const entityId = idParts.join(":");
      if (entityType && entityId) {
        updatePosition.mutate({
          entityType,
          entityId,
          body: { x: node.position.x, y: node.position.y },
        });
      }
    },
    [updatePosition]
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedEdgeId(null);
    const [kind, ...idParts] = node.id.split(":");
    setSelectedNodeType(kind ?? null);
    setSelectedNodeId(idParts.join(":"));
  }, []);

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedNodeId(null);
    setSelectedNodeType(null);
    setSelectedEdgeId((edge.data?.relationshipId as string) ?? null);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedNodeType(null);
    setSelectedEdgeId(null);
  }, []);

  if (graph.nodes.length === 0) {
    return null;
  }

  return (
    <div className="flex gap-4">
      <div className="relative min-h-[480px] flex-1 rounded-md border border-ink-100 bg-ink-50">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeDragStop={onNodeDragStop}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={3}
          defaultEdgeOptions={{ type: "relationshipEdge" }}
        >
          <Background gap={20} />
          <Controls />
          <MiniMap
            nodeColor={(n) => (n.data as Record<string, unknown>).color as string ?? "#64748b"}
            maskColor="rgba(255,255,255,0.7)"
          />
        </ReactFlow>
      </div>
      {selectedNodeId && selectedNodeType ? (
        <NodeDetailPanel
          entityType={selectedNodeType}
          entityId={selectedNodeId}
          detail={nodeDetail}
          onClose={() => {
            setSelectedNodeId(null);
            setSelectedNodeType(null);
          }}
        />
      ) : null}
      {selectedEdgeId ? (
        <EdgeDetailPanel
          detail={edgeDetail}
          onClose={() => setSelectedEdgeId(null)}
        />
      ) : null}
    </div>
  );
}
