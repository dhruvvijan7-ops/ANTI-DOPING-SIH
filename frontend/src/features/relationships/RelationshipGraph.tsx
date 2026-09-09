import { useMemo } from "react";
import type { RelationshipGraph as Graph } from "@/lib/api/types";

interface Placed {
  id: string;
  label: string;
  kind: string;
  is_subject: boolean;
  x: number;
  y: number;
}

const COLORS: Record<string, string> = {
  ATHLETE: "#14243a",
  SUPPORT_PERSON: "#0e7490",
  ORGANIZATION: "#7c2d12",
  default: "#64748b",
};

function layout(graph: Graph, size = { w: 760, h: 440 }): Placed[] {
  const cx = size.w / 2;
  const cy = size.h / 2;
  if (graph.nodes.length === 1) {
    const only = graph.nodes[0]!;
    return [{ id: only.id, label: only.label, kind: only.kind, is_subject: Boolean(only.is_subject), x: cx, y: cy }];
  }
  const subject = graph.nodes.find((n) => n.is_subject);
  const others = graph.nodes.filter((n) => !n.is_subject);
  const positions: Placed[] = [];
  if (subject) {
    positions.push({ id: subject.id, label: subject.label, kind: subject.kind, is_subject: true, x: cx, y: cy });
  }
  const radius = Math.min(size.w, size.h) * 0.36;
  others.forEach((node, i) => {
    const angle = (i / others.length) * 2 * Math.PI - Math.PI / 2;
    positions.push({
      id: node.id,
      label: node.label,
      kind: node.kind,
      is_subject: Boolean(node.is_subject),
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    });
  });
  if (!subject) {
    // No subject flagged: spread available nodes evenly.
    if (positions.length === 0) {
      return [];
    }
    return positions.map((p, i) => ({
      ...p,
      x: cx + radius * Math.cos((i / positions.length) * 2 * Math.PI),
      y: cy + radius * Math.sin((i / positions.length) * 2 * Math.PI),
    }));
  }
  return positions;
}

export function RelationshipGraphView({ graph }: { graph: Graph }) {
  const placed = useMemo(() => layout(graph), [graph]);
  const byId = useMemo(() => new Map(placed.map((p) => [p.id, p])), [placed]);

  if (placed.length === 0) {
    return <p className="py-10 text-center text-sm text-ink-500">No relationships to display.</p>;
  }

  const edgeLabel = (label: string) => label.replaceAll("_", " ");

  return (
    <svg viewBox="0 0 760 440" role="img" aria-label="Relationship graph" className="h-auto w-full rounded-md border border-ink-100 bg-white">
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <path d="M0,0 L8,3 L0,6 Z" fill="#94a3b8" />
        </marker>
      </defs>
      {graph.edges.map((edge) => {
        const s = byId.get(edge.source);
        const t = byId.get(edge.target);
        if (!s || !t) return null;
        const mx = (s.x + t.x) / 2;
        const my = (s.y + t.y) / 2 - 14;
        return (
          <g key={edge.id}>
            <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#cbd5e1" strokeWidth={1.5} markerEnd="url(#arrowhead)" />
            <text x={mx} y={my} textAnchor="middle" className="fill-ink-500 text-[10px]">
              {edgeLabel(edge.label)}
            </text>
          </g>
        );
      })}
      {placed.map((node) => {
        const color = COLORS[node.kind] ?? COLORS.default;
        return (
          <g key={node.id} transform={`translate(${node.x} ${node.y})`}>
            <circle r={node.is_subject ? 26 : 18} fill={color} stroke="#fff" strokeWidth={2} opacity={node.is_subject ? 1 : 0.85} />
            <text y={4.5} textAnchor="middle" className="fill-white text-[11px] font-semibold">
              {node.is_subject ? node.label.slice(0, 1).toUpperCase() : ""}
            </text>
            <text
              y={node.is_subject ? 44 : 34}
              textAnchor="middle"
              className={node.is_subject ? "fill-ink-900 text-[11px] font-semibold" : "fill-ink-600 text-[10px]"}
            >
              {node.label.length > 22 ? `${node.label.slice(0, 21)}…` : node.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}