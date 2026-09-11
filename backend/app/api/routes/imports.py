"""Batch data import APIs.

Implements the import workflow of master prompt §§11-27, §281-287:
upload/paste -> content-first format detection -> preview -> explicit column
mapping -> row validation + exact entity matching + dedupe -> explicit commit
(with partial-import support) -> cancellable at any point before commit.
Filename and MIME claims are never trusted (§597); nothing is silently
discarded (§24); commits are atomic and audited.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import Text, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permissions
from app.db.session import get_db
from app.importers import (
    BadUploadError,
    EmptyPayloadError,
    UnsupportedFormatError,
    apply_mapping_and_validate,
    commit_import,
    detect_format,
    parse_payload,
    sanitize_filename,
    sha256,
    store_parsed_rows,
)
from app.importers.detect import enforce_size_limit
from app.importers.pipeline import MAPPABLE_FIELDS
from app.models.identity import User
from app.models.imports import (
    ROW_READY,
    STATUS_CANCELED,
    STATUS_COMMITTED,
    STATUS_FAILED,
    DataImport,
    ImportRow,
    SOURCE_KIND_FILE,
    SOURCE_KIND_PASTE,
)
from app.security.rbac import Permissions
from app.services.audit_service import record_audit

router = APIRouter(tags=["imports"])

_READ = [Depends(require_permissions(Permissions.IMPORTS_READ))]
_CREATE = [Depends(require_permissions(Permissions.IMPORTS_CREATE))]
_COMMIT = [Depends(require_permissions(Permissions.IMPORTS_COMMIT))]

_MAX_PERMITTED_ROWS = 50_000


def _load(db: Session, import_id: uuid.UUID) -> DataImport:
    obj = db.get(DataImport, import_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Import not found")
    return obj


def _row_payload(row: ImportRow) -> dict:
    return {
        "row_number": row.row_number,
        "status": row.status,
        "original": row.original or {},
        "normalized": row.normalized or {},
        "errors": row.errors or [],
        "warnings": row.warnings or [],
        "dedupe_key": row.dedupe_key,
        "entity_match": row.entity_match,
        "report_id": str(row.report_id) if row.report_id else None,
    }


def _detail(db: Session, obj: DataImport, *, preview: bool = True) -> dict:
    rows = db.scalars(
        select(ImportRow).where(ImportRow.import_id == obj.id).order_by(ImportRow.row_number)
    ).all()
    summary = dict(obj.summary or {})
    summary["total"] = len(rows)
    return {
        "id": str(obj.id),
        "name": obj.name,
        "target": obj.target,
        "source_kind": obj.source_kind,
        "format": obj.format,
        "source_filename": obj.source_filename,
        "file_hash": obj.file_hash,
        "file_size": obj.file_size,
        "sheet_name": obj.sheet_name,
        "columns": obj.columns or [],
        "sheets": obj.sheets or [],
        "structure": obj.structure,
        "status": obj.status,
        "progress": obj.progress,
        "column_mapping": obj.column_mapping or {},
        "mappable_fields": sorted(f for f in MAPPABLE_FIELDS if f not in {"_skip", ""}),
        "inferred_types": obj.inferred_types or {},
        "summary": summary,
        "error_message": obj.error_message,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
        "validated_at": obj.validated_at.isoformat() if obj.validated_at else None,
        "committed_at": obj.committed_at.isoformat() if obj.committed_at else None,
        "canceled_at": obj.canceled_at.isoformat() if obj.canceled_at else None,
        "preview": [_row_payload(r) for r in rows[:50]] if preview else [],
    }


class PasteImportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    target: str = "INTELLIGENCE"
    source_kind: str = SOURCE_KIND_PASTE


class MappingRequest(BaseModel):
    mapping: dict[str, str] = Field(default_factory=dict)
    sheet_name: str | None = None


class CommitRequest(BaseModel):
    include_statuses: list[str] = Field(default_factory=lambda: [ROW_READY])


@router.post("/imports/upload", dependencies=_CREATE, summary="Upload a data file for import")
def upload_import(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    target: str = Form(default="INTELLIGENCE"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Receive a file, detect its format from content, and produce a preview."""
    raw = file.file.read() if file.file else b""
    safe_name = sanitize_filename(file.filename)
    try:
        if not raw:
            raise EmptyPayloadError("The uploaded file is empty.")
        enforce_size_limit(len(raw), paste=False)
        format_key = detect_format(safe_name, raw)
        parsed = parse_payload(raw, format_key=format_key, filename=safe_name)
    except BadUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    obj = DataImport(
        name=(name or safe_name or "Imported data").strip()[:255],
        target=target,
        source_kind=SOURCE_KIND_FILE,
        source_filename=safe_name,
        file_hash=sha256(raw),
        file_size=len(raw),
        payload=raw,
        created_by=user.id,
    )
    db.add(obj)
    db.flush()
    store_parsed_rows(db, obj, parsed)
    record_audit(
        db,
        actor_id=user.id,
        action="DATA_IMPORT_UPLOADED",
        entity_type="DATA_IMPORT",
        entity_id=str(obj.id),
        metadata={
            "format": obj.format,
            "filename": safe_name,
            "file_hash": obj.file_hash,
            "row_count": len(parsed.rows),
            "target": obj.target,
        },
    )
    db.commit()
    return _detail(db, obj)


@router.post("/imports/paste", dependencies=_CREATE, summary="Paste text/structured data for import")
def paste_import(
    body: PasteImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Ingest pasted CSV/JSON/TXT/TSV content via the same pipeline as a file."""
    raw = body.content.encode("utf-8", errors="replace")
    try:
        enforce_size_limit(len(raw), paste=True)
        try:
            format_key = detect_format(None, raw)
        except UnsupportedFormatError:
            format_key = "TXT"
        parsed = parse_payload(raw, format_key=format_key)
    except BadUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if len(parsed.rows) > _MAX_PERMITTED_ROWS:
        raise HTTPException(
            status_code=422,
            detail=f"Pasted import exceeds the {_MAX_PERMITTED_ROWS} row limit.",
        )

    obj = DataImport(
        name=body.name.strip()[:255],
        target=body.target,
        source_kind=SOURCE_KIND_PASTE,
        source_filename=None,
        file_hash=sha256(raw),
        file_size=len(raw),
        payload=raw,
        created_by=user.id,
    )
    db.add(obj)
    db.flush()
    store_parsed_rows(db, obj, parsed)
    db.commit()
    return _detail(db, obj)


@router.get("/imports", dependencies=_READ, summary="List data imports")
def list_imports(
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    own_only: bool = Query(default=False),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    stmt = select(DataImport)
    if status_filter:
        stmt = stmt.where(DataImport.status == status_filter.upper())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                DataImport.name.ilike(like),
                DataImport.source_filename.ilike(like),
                DataImport.format.ilike(like),
            )
        )
    if own_only:
        stmt = stmt.where(DataImport.created_by == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(DataImport.created_at.desc()).offset(offset).limit(limit)).all()
    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "imports": [_detail(db, i, preview=False) for i in items],
    }


@router.get("/imports/{import_id}", dependencies=_READ, summary="Import detail with preview")
def import_detail(import_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return _detail(db, _load(db, import_id))


@router.get("/imports/{import_id}/rows", dependencies=_READ, summary="Page through import rows")
def import_rows(
    import_id: uuid.UUID,
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    obj = _load(db, import_id)
    stmt = select(ImportRow).where(ImportRow.import_id == obj.id)
    if status_filter:
        stmt = stmt.where(ImportRow.status == status_filter.upper())
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                ImportRow.original.cast(Text).ilike(like),
                ImportRow.normalized.cast(Text).ilike(like),
                ImportRow.errors.cast(Text).ilike(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ImportRow.row_number).offset(offset).limit(limit)
    ).all()
    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "import_id": str(obj.id),
        "rows": [_row_payload(r) for r in rows],
    }


@router.post("/imports/{import_id}/mapping", dependencies=_CREATE, summary="Set column mapping and validate")
def set_mapping(
    import_id: uuid.UUID,
    body: MappingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    obj = _load(db, import_id)
    if obj.status in (STATUS_COMMITTED, STATUS_CANCELED, STATUS_FAILED):
        raise HTTPException(status_code=409, detail=f"Import status {obj.status} forbids mapping changes.")

    if (
        body.sheet_name
        and obj.format == "XLSX"
        and body.sheet_name != obj.sheet_name
        and body.sheet_name in (obj.sheets or [])
        and obj.payload
    ):
        parsed = parse_payload(obj.payload, format_key=obj.format, filename=obj.source_filename, sheet_name=body.sheet_name)
        store_parsed_rows(db, obj, parsed)
        db.flush()

    try:
        summary = apply_mapping_and_validate(db, obj, mapping=body.mapping or None)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        db.rollback()
        import_ob = _load(db, import_id)
        if import_ob.status != STATUS_FAILED:
            import_ob.status = STATUS_FAILED
            import_ob.error_message = "Validation failed unexpectedly."
            db.commit()
        raise

    record_audit(
        db,
        actor_id=user.id,
        action="DATA_IMPORT_VALIDATED",
        entity_type="DATA_IMPORT",
        entity_id=str(obj.id),
        metadata={"summary": {k: v for k, v in summary.items() if k != "parsing_warnings"}},
    )
    db.commit()
    return _detail(db, obj)


@router.post("/imports/{import_id}/validate", dependencies=_CREATE, summary="Re-run validation")
def revalidate(
    import_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    obj = _load(db, import_id)
    if obj.status not in ("PARSED", "VALIDATED"):
        raise HTTPException(status_code=409, detail=f"Import status {obj.status} forbids validation.")
    try:
        summary = apply_mapping_and_validate(db, obj, mapping=None)
    except Exception:
        db.rollback()
        raise

    record_audit(
        db,
        actor_id=user.id,
        action="DATA_IMPORT_VALIDATED",
        entity_type="DATA_IMPORT",
        entity_id=str(obj.id),
        metadata={"summary": {k: v for k, v in summary.items() if k != "parsing_warnings"}},
    )
    db.commit()
    return _detail(db, obj)


@router.post("/imports/{import_id}/commit", dependencies=_COMMIT, summary="Commit selected rows into intelligence")
def do_commit(
    import_id: uuid.UUID,
    body: CommitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    obj = _load(db, import_id)
    if obj.status == STATUS_CANCELED:
        raise HTTPException(status_code=409, detail="This import was canceled.")
    try:
        summary = commit_import(db, obj, include_statuses=body.include_statuses, actor=user.id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        db.rollback()
        obj = _load(db, import_id)
        if obj.status != STATUS_FAILED:
            obj.status = STATUS_FAILED
            obj.error_message = "Commit failed unexpectedly."
            db.commit()
        raise

    record_audit(
        db,
        actor_id=user.id,
        action="DATA_IMPORT_COMMITTED",
        entity_type="DATA_IMPORT",
        entity_id=str(obj.id),
        metadata={
            "imported": summary.get("imported"),
            "rejected": summary.get("rejected"),
            "report_ids": summary.get("report_ids", [])[:200],
        },
    )
    db.commit()
    return _detail(db, obj)


@router.post("/imports/{import_id}/cancel", dependencies=_CREATE, summary="Cancel an import before commit")
def cancel_import(
    import_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    obj = _load(db, import_id)
    if obj.committed_at is not None:
        raise HTTPException(status_code=409, detail="A committed import cannot be canceled.")
    obj.status = STATUS_CANCELED
    obj.canceled_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor_id=user.id,
        action="DATA_IMPORT_CANCELED",
        entity_type="DATA_IMPORT",
        entity_id=str(obj.id),
        metadata={"name": obj.name},
    )
    db.commit()
    return _detail(db, obj)


__all__ = ["router"]