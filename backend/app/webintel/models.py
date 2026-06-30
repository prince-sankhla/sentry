from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WebEvidence(Base):
    __tablename__ = "web_evidence"
    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_web_evidence_content_hash"),
        Index("ix_web_evidence_url", "url"),
        Index("ix_web_evidence_query", "query"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    query: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    procurement_evidence: Mapped["WebProcurementEvidence | None"] = relationship(
        back_populates="web_evidence",
        cascade="all, delete-orphan",
        uselist=False,
    )


class WebProcurementEvidence(Base):
    __tablename__ = "web_procurement_evidence"
    __table_args__ = (
        UniqueConstraint("web_evidence_id", name="uq_web_procurement_evidence_web_evidence_id"),
        Index("ix_web_procurement_evidence_normalized_company_name", "normalized_company_name"),
        Index("ix_web_procurement_evidence_government_buyer", "government_buyer"),
        Index("ix_web_procurement_evidence_tender_number", "tender_number"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    web_evidence_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("web_evidence.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tender_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tenders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    award_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("awards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    normalized_company_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    government_buyer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tender_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    tender_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    procurement_sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    award_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tender_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(500), nullable=True)
    people_mentioned: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    related_companies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    raw_signals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    web_evidence: Mapped[WebEvidence] = relationship(back_populates="procurement_evidence")
