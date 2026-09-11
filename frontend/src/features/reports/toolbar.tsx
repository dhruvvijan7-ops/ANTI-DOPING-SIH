import { Bold, Heading2, Italic, List, ListOrdered, Quote, Table2, Underline } from "lucide-react";
import type { DocumentBlock } from "@/lib/api/types";

interface ToolbarProps {
  onAddBlock: (type: DocumentBlock["type"], attrs?: Record<string, unknown>) => void;
  activeBlock: DocumentBlock | null;
  onToggleAttr: (key: string, value: unknown) => void;
}

const btn =
  "inline-flex h-8 w-8 items-center justify-center rounded-md text-ink-600 transition-colors hover:bg-ink-100 hover:text-ink-900 disabled:cursor-not-allowed disabled:opacity-40";

export function EditorToolbar({ onAddBlock, activeBlock, onToggleAttr }: ToolbarProps) {
  const attrs = activeBlock?.attrs ?? {};
  return (
    <div className="flex flex-wrap items-center gap-1 border-b border-ink-100 bg-white px-3 py-1.5">
      <span className="mr-1 text-xs font-medium uppercase tracking-wide text-ink-400">Format</span>
      <button type="button" title="Bold" className={btn} disabled={!activeBlock} onClick={() => onToggleAttr("bold", !attrs.bold)}>
        <Bold className="h-4 w-4" />
      </button>
      <button type="button" title="Italic" className={btn} disabled={!activeBlock} onClick={() => onToggleAttr("italic", !attrs.italic)}>
        <Italic className="h-4 w-4" />
      </button>
      <button type="button" title="Underline" className={btn} disabled={!activeBlock} onClick={() => onToggleAttr("underline", !attrs.underline)}>
        <Underline className="h-4 w-4" />
      </button>
      <span className="mx-1 h-5 w-px bg-ink-100" />
      <span className="mr-1 text-xs font-medium uppercase tracking-wide text-ink-400">Blocks</span>
      <button type="button" title="Heading" className={btn} onClick={() => onAddBlock("heading", { level: 2 })}>
        <Heading2 className="h-4 w-4" />
      </button>
      <button type="button" title="Bullet list" className={btn} onClick={() => onAddBlock("list")}>
        <List className="h-4 w-4" />
      </button>
      <button type="button" title="Numbered list" className={btn} onClick={() => onAddBlock("list", { ordered: true })}>
        <ListOrdered className="h-4 w-4" />
      </button>
      <button type="button" title="Quote" className={btn} onClick={() => onAddBlock("quote")}>
        <Quote className="h-4 w-4" />
      </button>
      <button type="button" title="Table" className={btn} onClick={() => onAddBlock("table")}>
        <Table2 className="h-4 w-4" />
      </button>
      <span className="ml-auto text-xs text-ink-400">
        Block: {activeBlock ? activeBlock.type.replace("_", " ") : "—"}
      </span>
    </div>
  );
}