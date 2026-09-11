"""Data import domain: batch ingestion with row-level provenance.

An import is a first-class, auditable unit of work (§11-§26). Every row keeps its
original cell contents alongside the normalized values used downstream so that
imported intelligence can be traced back to the exact source row and field
(§18, §603-§607). Format detection is content-based, never extension/subjective
(§597-§599); rows are never silently discarded (§24); commits are explicit and
reversible by policy (§281-§287, §602).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

DEFAULT_TARGET = "INTELLIGENCE"
IMPORT_TARGETS = (DEFAULT_TARGET,)

# Source kinds indicate origin: a physical file upload vs a paste entry.
SOURCE_KIND_FILE = "FILE"
SOURCE_KIND_PASTE = "PASTE"

# Supported file formats. XLS is intentionally not read (no OCR/legacy support):
# it fails with an explicit error instead of misparsing (condition §598).
FORMAT_CSV = "CSV"
FORMAT_TSV = "TSV"
FORMAT_JSON = "JSON"
FORMAT_XLSX = "XLSX"
FORMAT_XLS = "XLS"
FORMAT_DOCX = "DOCX"
FORMAT_PDF = "PDF"
FORMAT_TXT = "TXT"
SUPPORTED_FORMATS = (FORMAT_CSV, FORMAT_TSV, FORMAT_JSON, FORMAT_XLSX, FORMAT_DOCX, FORMAT_PDF, FORMAT_TXT)

# Import lifecycle (progress is an integer 0-100 used by the UI).
STATUS_UPLOADED = "UPLOADED"
STATUS_PARSED = "PARSED"
STATUS_VALIDATED = "VALIDATED"
STATUS_COMMITTED = "COMMITTED"
STATUS_PARTIAL = "PARTIAL"
STATUS_FAILED = "FAILED"
STATUS_CANCELED = "CANCELED"
IMPORT_STATUSES = (
    STATUS_UPLOADED,
    STATUS_PARSED,
    STATUS_VALIDATED,
    STATUS_COMMITTED,
    STATUS_PARTIAL,
    STATUS_FAILED,
    STATUS_CANCELED,
)

# Per-row statuses (review buckets are surfaced for explicit user decisions).
ROW_READY = "READY"
ROW_REVIEW = "REVIEW"  # data valid but no entity resolved yet
ROW_DUPLICATE = "DUPLICATE"
ROW_INVALID = "INVALID"
ROW_IMPORTED = "IMPORTED"
ROW_REJECTED = "REJECTED"
ROW_STATUSES = (
    ROW_READY,
    ROW_REVIEW,
    ROW_DUPLICATE,
    ROW_INVALID,
    ROW_IMPORTED,
    ROW_REJECTED,
)

# Commit eligibility: only rows an operator explicitly opts in to.
COMMIT_OK_BY_DEFAULT = (ROW_READY,)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class DataImport(Base):
    __tablename__ = "data_imports"
    __table_args__ = (
        Index("ix_data_imports_owner_time", "created_by", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[str] = mapped_column(String(32), default=DEFAULT_TARGET, nullable=False)
    source_kind: Mapped[str] = mapped_column(
        String(16), default=SOURCE_KIND_FILE, nullable=False, index=True
    )
    format: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    sheet_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    columns: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    sheets: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    structure: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=STATUS_UPLOADED, nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    column_mapping: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    inferred_types: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rows: Mapped[list["ImportRow"]] = relationship(
        back_populates="import_", cascade="all, delete-orphan", passive_deletes=True
    )


class ImportRow(Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        Index("ix_import_rows_import_number", "import_id", "row_number"),
        Index("ix_import_rows_import_status", "import_id", "status"),
        Index("ix_import_rows_dedupe", "import_id", "dedupe_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    import_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("data_imports.id", ondelete="CASCADE"), nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ROW_READY, nullable=False, index=True)
    original: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    normalized: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    errors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    field_provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    entity_match: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("intelligence_reports.id", ondelete="SET NULL"), nullable=True
    )

    import_: Mapped["DataImport"] = relationship(back_populates="rows")