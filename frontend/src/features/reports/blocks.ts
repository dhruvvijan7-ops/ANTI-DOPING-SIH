// Report document block model helpers (Reporting gate).
// Blocks mirror the backend schema in ReportTypes. Each block carries structured
// provenance so AI-generated content is distinguishable at the data level.

import type { BlockProvenanceKind, DocumentBlock } from "@/lib/api/types";

export const BLOCK_PROVENANCE_LABEL: Record<BlockProvenanceKind, string> = {
  human: "Human authored",
  ai: "AI generated",
  ai_edited: "AI generated, edited by human",
};

export function makeBlock(
  type: DocumentBlock["type"],
  overrides: Partial<DocumentBlock> = {},
  provenance: BlockProvenanceKind = "human",
): DocumentBlock {
  return {
    id: `blk-${crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)}`,
    type,
    text: "",
    attrs: {},
    items: [],
    head: [],
    rows: [],
    provenance: { kind: provenance, refs: [] },
    ...overrides,
  };
}

export function countWords(blocks: DocumentBlock[] | undefined): number {
  if (!blocks) return 0;
  let n = 0;
  for (const b of blocks) {
    if (b.type === "table") {
      for (const row of b.rows ?? []) n += row.join(" ").split(/\s+/).filter(Boolean).length;
      for (const h of b.head ?? []) n += h.split(/\s+/).filter(Boolean).length;
    } else if (b.type === "list") {
      for (const item of b.items ?? []) n += item.split(/\s+/).filter(Boolean).length;
    } else {
      n += (b.text ?? "").split(/\s+/).filter(Boolean).length;
    }
  }
  return n;
}

export function lastSavedLabel(savedAt: string | null | undefined): string {
  if (!savedAt) return "Not saved yet";
  try {
    return `Saved ${new Date(savedAt).toLocaleTimeString()}`;
  } catch {
    return "Saved";
  }
}