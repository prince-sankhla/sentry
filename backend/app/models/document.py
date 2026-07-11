from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("tender_id", "title", name="uq_documents_tender_title"),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="attachment", index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    file_extension: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    source_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # -- evidence provenance (Phase 4) -----------------------------------
    connector_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    connector_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    evidence_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    import_run_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True, index=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    archive_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mirror_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tender: Mapped["Tender"] = relationship(back_populates="documents")
