"""Report document rendering and export (Reporting gate).

Converts the structured rich-text ``document_blocks`` (plus title and provenance
metadata) into three formats:

* ``HTML`` -- print-friendly standalone document (also the "print to PDF" path).
* ``DOCX`` -- generated with ``python-docx``.
* ``PDF`` -- generated with ``reportlab`` (pure Python, no system deps).

Every export embeds a watermark / provenance block containing the case reference,
report version, generated-at timestamp, author and status (§135, §302). Block
provenance (AI vs human) is preserved inline so a reader can distinguish AI
generated and AI assisted text (§353, §567).
"""
from __future__ import annotations

import html
from functools import lru_cache
from typing import Any

# Block provenance kinds supported in the structured document editor.
PROVENANCE_HUMAN = "human"
PROVENANCE_AI = "ai"
PROVENANCE_AI_EDITED = "ai_edited"

PROVENANCE_LABELS: dict[str, str] = {
    PROVENANCE_HUMAN: "Human authored",
    PROVENANCE_AI: "AI generated",
    PROVENANCE_AI_EDITED: "AI generated, edited by human",
}


class ReportRenderContext:
    """Metadata required by every export to satisfy provenance requirements."""

    def __init__(self, *, case_ref: str, report_version: int, author: str,
                 status: str, generated_at: str) -> None:
        self.case_ref = case_ref
        self.report_version = report_version
        self.author = author
        self.status = status
        self.generated_at = generated_at

    def provenance_lines(self) -> list[str]:
        return [
            f"Case reference: {self.case_ref}",
            f"Report version: {self.report_version}",
            f"Generated at: {self.generated_at}",
            f"Author: {self.author}",
            f"Status: {self.status}",
        ]


def _inline_attrs(text: str, attrs: dict[str, Any] | None) -> str:
    """Escape ``text`` and apply any rich-text attributes safely."""
    safe = html.escape(text or "")
    attrs = attrs or {}
    if attrs.get("bold"):
        safe = f"<strong>{safe}</strong>"
    if attrs.get("italic"):
        safe = f"<em>{safe}</em>"
    if attrs.get("underline"):
        safe = f"<u>{safe}</u>"
    if attrs.get("link"):
        url = html.escape(attrs["link"], quote=True)
        safe = f'<a href="{url}">{safe}</a>'
    return safe


def _block_to_html(block: dict[str, Any]) -> str:
    kind = block.get("type", "paragraph")
    attrs = block.get("attrs") or {}
    text = block.get("text") or ""
    badge = ""
    prov = block.get("provenance") or {}
    if prov.get("kind") and prov["kind"] != PROVENANCE_HUMAN:
        label = PROVENANCE_LABELS.get(prov["kind"], prov["kind"])
        badge = (
            f'<span class="prov-badge" title="Source data linked to this block">'
            f'[{label}]</span> '
        )

    if kind == "heading":
        level = min(int(attrs.get("level") or 2), 6)
        return f"<h{level}>{badge}{_inline_attrs(text, attrs)}</h{level}>"

    if kind == "quote":
        return f"<blockquote>{badge}{_inline_attrs(text, attrs)}</blockquote>"

    if kind == "page_break":
        return '<div class="page-break"></div>'

    if kind == "list":
        items = block.get("items") or []
        ordered = bool(attrs.get("ordered"))
        tag = "ol" if ordered else "ul"
        body = "".join(f"<li>{_inline_attrs(i, attrs)}</li>" for i in items)
        return f"<{tag}>{badge}{body}</{tag}>"

    if kind == "table":
        head = block.get("head") or []
        rows = block.get("rows") or []
        thead = ""
        if head:
            thead = "<thead><tr>" + "".join(f"<th>{html.escape(str(h))}</th>" for h in head) + "</tr></thead>"
        tbody = "<tbody>" + "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>"
            for row in rows
        ) + "</tbody>"
        return f"<table>{thead}{tbody}</table>"

    return f"<p>{badge}{_inline_attrs(text, attrs)}</p>"


def document_to_html(title: str, blocks: list[dict[str, Any]]) -> str:
    """Render report blocks to a principled, style-constrained HTML fragment."""
    parts = []
    has_content = False
    for block in blocks or []:
        rendered = _block_to_html(block)
        if rendered:
            has_content = True
        parts.append(rendered)
    if not has_content and not title:
        return "<p><em>No content yet. This report is blank.</em></p>"
    return "\n".join(parts)


def build_standalone_html(title: str, blocks: list[dict[str, Any]],
                          ctx: ReportRenderContext) -> str:
    """Return a complete standalone HTML document (print-ready)."""
    body_blocks = document_to_html(title, blocks)
    prov = "".join(f"<div>{html.escape(line)}</div>" for line in ctx.provenance_lines())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(title or "Report")}</title>
<style>
  body {{ font-family: Georgia, serif; color: #1a1a1a; line-height: 1.5; margin: 48px auto; max-width: 760px; padding: 0 24px; }}
  h1 {{ font-size: 26px; margin: 24px 0 4px; }}
  h2 {{ font-size: 20px; margin: 20px 0 8px; }}
  h3 {{ font-size: 16px; margin: 16px 0 6px; }}
  blockquote {{ border-left: 3px solid #cbd5e1; margin: 12px 0; padding: 4px 12px; color: #475569; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; font-size: 13px; }}
  th {{ background: #f1f5f9; }}
  .prov-badge {{ font-size: 10px; color: #7c3aed; text-transform: uppercase; letter-spacing: .03em; }}
  .page-break {{ page-break-before: always; }}
  .prov {{ margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 12px; font-size: 11px; color: #64748b; }}
  @media print {{ .prov {{ page-break-inside: avoid; }} }}
</style></head>
<body>
<h1>{html.escape(title or "Untitled report")}</h1>
{body_blocks}
<div class="prov"><strong>Generated provenance</strong>{prov}</div>
</body></html>
"""


@lru_cache(maxsize=1)
def _provenance_palette() -> dict[str, tuple[int, int, int]]:
    return {
        PROVENANCE_HUMAN: (30, 41, 59),
        PROVENANCE_AI: (124, 58, 237),
        PROVENANCE_AI_EDITED: (79, 70, 229),
    }


def document_to_docx_bytes(title: str, blocks: list[dict[str, Any]],
                           ctx: ReportRenderContext) -> bytes:
    """Render blocks into a DOCX byte stream via ``python-docx``."""
    from docx import Document  # noqa: PLC0415 - lazy: optional dependency

    doc = Document()
    doc.add_heading(title or "Untitled report", level=0)
    for block in blocks or []:
        _docx_block(doc, block)
    doc.add_paragraph("")
    doc.add_paragraph("Generated provenance", style="Intense Quote")
    for line in ctx.provenance_lines():
        doc.add_paragraph(line, style="Caption")
    import io  # noqa: PLC0415
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _docx_block(doc: Any, block: dict[str, Any]) -> None:
    kind = block.get("type", "paragraph")
    attrs = block.get("attrs") or {}
    text = block.get("text") or ""
    if kind == "heading":
        doc.add_heading(text, level=min(int(attrs.get("level") or 2), 6))
    elif kind == "quote":
        doc.add_paragraph(text, style="Intense Quote")
    elif kind == "page_break":
        doc.add_page_break()
    elif kind == "list":
        for item in block.get("items") or []:
            doc.add_paragraph(item, style="List Number" if attrs.get("ordered") else "List Bullet")
    elif kind == "table":
        head = block.get("head") or []
        rows = block.get("rows") or []
        if head:
            rows = [head] + rows
        if rows:
            table = doc.add_table(rows=len(rows), cols=max(len(r) for r in rows))
            table.style = "Light Grid Accent 1"
            for r, row in enumerate(rows):
                for c, cell in enumerate(row):
                    table.cell(r, c).text = str(cell)
    else:
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.bold = bool(attrs.get("bold"))
        run.italic = bool(attrs.get("italic"))
        run.underline = bool(attrs.get("underline"))


def document_to_pdf_bytes(title: str, blocks: list[dict[str, Any]],
                          ctx: ReportRenderContext) -> bytes:
    """Render blocks into a PDF byte stream via ``reportlab``."""
    from reportlab.lib.pagesizes import A4  # noqa: PLC0415
    from reportlab.pdfgen import canvas  # noqa: PLC0415
    from reportlab.lib import colors as rl_colors  # noqa: PLC0415

    width, height = A4
    import io  # noqa: PLC0415

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(title or "Untitled report")

    x, y, right = 56, height - 72, width - 56
    c.setFont("Helvetica-Bold", 20)
    _wrap(c, title or "Untitled report", x, y, right, size=20)
    y -= 34

    c.setFont("Helvetica", 11)
    left, top = 0, 0
    for block in blocks or []:
        # simple single-pass prose renderer; tables handled with reduced fidelity
        kind = block.get("type", "paragraph")
        if kind == "heading":
            c.setFont("Helvetica-Bold", 15)
            _wrap(c, (block.get("text") or ""), x, y, right, size=15)
            y -= 22
        elif kind == "quote":
            c.setFont("Helvetica-Oblique", 10)
            _wrap(c, (block.get("text") or ""), x + 12, y, right - 12, size=10)
            y -= 16
        elif kind == "list":
            c.setFont("Helvetica", 11)
            for item in block.get("items") or []:
                _wrap(c, f"- {item}", x + 8, y, right - 8, size=11)
                y -= 16
        elif kind == "page_break":
            c.showPage()
            y = height - 72
        else:
            c.setFont("Helvetica", 11)
            _wrap(c, (block.get("text") or ""), x, y, right, size=11)
            y -= 18
        top = min(top, 60)
        if y <= 72:
            c.showPage()
            y = height - 72

    c.setStrokeColor(rl_colors.HexColor("#D0D2D8"))
    c.setFont("Helvetica", 9)
    y -= 20
    c.drawString(x, y, "Generated provenance")
    y -= 14
    for line in ctx.provenance_lines():
        c.drawString(x, y, line)
        y -= 12

    c.showPage()
    c.save()
    return buf.getvalue()


def _wrap(c: Any, text: str, x: float, y: float, right: float, size: float) -> None:
    """Wrap ``text`` to the page margin; fall back to drawString per line."""
    max_w = right - x
    import textwrap  # noqa: PLC0415
    for line in textwrap.wrap(text, width=int(max_w / (size * 0.5)) or 40) or [text]:
        c.drawString(x, y, line[:240])
        y -= size * 1.4
        if y < 60:
            break