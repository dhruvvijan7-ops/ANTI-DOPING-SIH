"""Structured report document schemas (Reporting gate).

Validates the rich-text block model used by the in-app word-like editor. Every
block carries structured provenance so AI-generated content is distinguishable
from human-authored text at the data level (§567), and inserted/grounded blocks
can carry references to the case records they were generated from.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

BlockKind = Literal["paragraph", "heading", "list", "table", "quote", "page_break"]

ProvenanceKind = Literal["human", "ai", "ai_edited"]


class BlockProvenance(BaseModel):
    """Who produced a block and which case records ground it.

    ``kind`` distinguishes human vs AI content. ``refs`` lists the DB entities
    (evidence, intelligence, timeline event, finding, source) that support the
    block, satisfying source attribution (§131, §571).
    """

    kind: ProvenanceKind = "human"
    refs: list[dict[str, Any]] = Field(default_factory=list)


class DocumentBlock(BaseModel):
    """One structured rich-text block."""

    id: str = Field(default="", max_length=64)
    type: BlockKind = "paragraph"
    text: str | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)
    items: list[str] = Field(default_factory=list)
    head: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    provenance: BlockProvenance = Field(default_factory=BlockProvenance)

    @field_validator("id")
    @classmethod
    def _id_required(cls, v: str) -> str:
        return v or "blk"

    def to_storage(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class DocumentBlocksBody(BaseModel):
    """Payload to save a report's structured document."""

    blocks: list[DocumentBlock] = Field(default_factory=list)
    title: str | None = None
    # When True, only the autosave draft columns are written (not persisted as
    # the working version). Autosave must never destroy user text (§564).
    autosave: bool = False


class ReportTypeBody(BaseModel):
    report_type: Literal["MANUAL", "AI_ASSISTED", "HYBRID"]


def normalize_blocks(raw: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Validate and normalize a raw block list for storage."""
    if not raw:
        return []
    return [DocumentBlock.model_validate(b).to_storage() for b in raw]