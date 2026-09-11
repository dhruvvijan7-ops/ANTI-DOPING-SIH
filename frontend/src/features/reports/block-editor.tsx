import { Plus } from "lucide-react";
import type { DocumentBlock } from "@/lib/api/types";
import { BLOCK_PROVENANCE_LABEL } from "./blocks";

interface BlockEditorProps {
  blocks: DocumentBlock[];
  activeId: string | null;
  onActive: (id: string | null) => void;
  onChange: (id: string, patch: Partial<DocumentBlock>) => void;
  onInsertAfter: (id: string) => void;
  onRemove: (id: string) => void;
}

export function BlockEditor({ blocks, activeId, onActive, onChange, onInsertAfter, onRemove }: BlockEditorProps) {
  if (!blocks.length) {
    return (
      <div
        className="rounded-lg border-2 border-dashed border-ink-200 bg-white px-6 py-10 text-center"
        onFocus={() => onActive(null)}
      >
        <p className="text-sm text-ink-500">This report is blank. Start writing above, or insert case data from the sidebar.</p>
        <p className="mt-1 text-xs text-ink-400">Use the toolbar to add headings, lists, quotes, tables and more.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {blocks.map((block, i) => {
        const active = activeId === block.id;
        return (
          <BlockRow
            key={block.id}
            block={block}
            index={i}
            active={active}
            onFocus={() => onActive(block.id)}
            onChange={(patch) => onChange(block.id, patch)}
            onInsertAfter={() => onInsertAfter(block.id)}
            onRemove={() => onRemove(block.id)}
          />
        );
      })}
    </div>
  );
}

interface BlockRowProps {
  block: DocumentBlock;
  index: number;
  active: boolean;
  onFocus: () => void;
  onChange: (patch: Partial<DocumentBlock>) => void;
  onInsertAfter: () => void;
  onRemove: () => void;
}

function BlockRow({ block, index, active, onFocus, onChange, onInsertAfter, onRemove }: BlockRowProps) {
  const prov = block.provenance?.kind ?? "human";
  return (
    <div
      className={`group relative rounded-md border transition-colors ${active ? "border-signal-300 bg-white ring-1 ring-signal-100" : "border-transparent hover:border-ink-100"}`}
      onFocus={onFocus}
      onBlur={() => {}}
    >
      <div className="flex items-center p-2">
        <span className="mr-2 w-6 shrink-0 text-right font-mono text-xs text-ink-300">{index + 1}</span>
        <div className="min-w-0 flex-1">
          <BlockField block={block} onChange={onChange} />
        </div>
      </div>

      <div className={`absolute -right-2 top-2 flex items-center gap-1 transition-opacity ${active ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
        <button
          type="button"
          title="Insert block after"
          onClick={onInsertAfter}
          className="rounded-md border border-ink-200 bg-white p-1 text-ink-500 hover:bg-ink-50 hover:text-ink-900"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          title="Remove block"
          onClick={onRemove}
          className="rounded-md border border-ink-200 bg-white p-1 text-red-500 hover:bg-red-50"
        >
          <span className="block h-3.5 w-3.5 text-xs leading-none">×</span>
        </button>
        <span
          title={BLOCK_PROVENANCE_LABEL[prov]}
          className={`rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${
            prov === "ai" ? "bg-violet-50 text-violet-700" : prov === "ai_edited" ? "bg-indigo-50 text-indigo-700" : "bg-ink-50 text-ink-400"
          }`}
        >
          {prov === "ai" ? "AI" : prov === "ai_edited" ? "AI·H" : "H"}
        </span>
      </div>
    </div>
  );
}

function BlockField({ block, onChange }: { block: DocumentBlock; onChange: (patch: Partial<DocumentBlock>) => void }) {
  switch (block.type) {
    case "heading":
      return (
        <input
          value={block.text ?? ""}
          onChange={(e) => onChange({ text: e.target.value })}
          placeholder="Heading"
          className={`w-full bg-transparent font-display font-semibold text-ink-900 outline-none ${
            block.attrs?.level === 1 ? "text-2xl" : "text-lg"
          }`}
          style={{ fontWeight: block.attrs?.bold ? 700 : undefined }}
        />
      );
    case "quote":
      return (
        <textarea
          value={block.text ?? ""}
          onChange={(e) => onChange({ text: e.target.value })}
          placeholder="Quote text"
          rows={1}
          className="w-full resize-none border-l-4 border-ink-200 bg-transparent py-1 pl-3 text-sm italic text-ink-700 outline-none"
        />
      );
    case "page_break":
      return <div className="text-center text-xs uppercase tracking-widest text-ink-300">— Page break —</div>;
    case "list":
      return <ListField block={block} onChange={onChange} />;
    case "table":
      return <TableField block={block} onChange={onChange} />;
    default:
      return (
        <textarea
          value={block.text ?? ""}
          onChange={(e) => onChange({ text: e.target.value })}
          placeholder="Paragraph"
          rows={1}
          className="w-full resize-none bg-transparent py-1 text-sm leading-6 text-ink-800 outline-none"
          style={{
            fontWeight: block.attrs?.bold ? 700 : undefined,
            fontStyle: block.attrs?.italic ? "italic" : undefined,
            textDecoration: block.attrs?.underline ? "underline" : undefined,
          }}
        />
      );
  }
}

function ListField({ block, onChange }: { block: DocumentBlock; onChange: (patch: Partial<DocumentBlock>) => void }) {
  const items = block.items && block.items.length ? block.items : [""];
  const update = (i: number, value: string) => {
    const next = [...items];
    next[i] = value;
    if (i === next.length - 1 && value.trim() !== "") {
      next.push("");
    }
    if (i < next.length - 1 && value.trim() === "" && next.length > 1) {
      next.splice(i, 1);
    }
    onChange({ items: next });
  };
  return (
    <ul className={block.attrs?.ordered ? "list-decimal" : "list-disc"} style={{ listStylePosition: "inside" }}>
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-1">
          <input
            value={item}
            onChange={(e) => update(i, e.target.value)}
            placeholder="List item"
            className="w-full bg-transparent py-0.5 text-sm text-ink-800 outline-none"
          />
        </li>
      ))}
    </ul>
  );
}

function TableField({ block, onChange }: { block: DocumentBlock; onChange: (patch: Partial<DocumentBlock>) => void }) {
  const head = block.head?.length ? block.head : [""];
  const rows = block.rows?.length ? block.rows : [[""]];

  const updateHead = (i: number, value: string) => {
    const next = [...head];
    next[i] = value;
    onChange({ head: next });
  };
  const updateCell = (r: number, c: number, value: string) => {
    const next = rows.map((row) => [...row]);
    const target = next[r];
    if (!target) return;
    target[c] = value;
    onChange({ rows: next });
  };
  const addRow = () => onChange({ rows: [...rows, Array(head.length).fill("")] });

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {head.map((h, c) => (
              <th key={c} className="border border-ink-200 bg-ink-50 p-1">
                <input
                  value={h}
                  onChange={(e) => updateHead(c, e.target.value)}
                  placeholder={`Col ${c + 1}`}
                  className="w-full bg-transparent text-xs font-medium text-ink-700 outline-none"
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r}>
              {Array.from({ length: Math.max(head.length, row.length) }).map((_, c) => (
                <td key={c} className="border border-ink-200 p-1">
                  <input
                    value={row[c] ?? ""}
                    onChange={(e) => updateCell(r, c, e.target.value)}
                    placeholder=""
                    className="w-full bg-transparent text-xs text-ink-800 outline-none"
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <button type="button" onClick={addRow} className="mt-1 text-xs text-signal-700 hover:underline">
        + Add row
      </button>
    </div>
  );
}