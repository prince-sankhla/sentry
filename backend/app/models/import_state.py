from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ImportCheckpoint(Base):
    __tablename__ = "import_checkpoints"
    __table_args__ = (UniqueConstraint("source", name="uq_import_checkpoints_source"),)

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_processed_page: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_processed_record: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_successful_import_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_imports: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True, default="pending")
    current_page: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_record: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_records: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    downloaded_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_tenders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_companies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_awards: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_imports: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SourceRecordVersion(Base):
    __tablename__ = "source_record_versions"
    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "source_record_id",
            "content_hash",
            name="uq_source_record_versions_source_record_hash",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_record_id: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False, default="imported", index=True)
    snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
