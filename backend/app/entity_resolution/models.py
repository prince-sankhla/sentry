from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CanonicalCompany(Base):
    __tablename__ = "canonical_companies"
    __table_args__ = (
        UniqueConstraint("canonical_key", name="uq_canonical_companies_canonical_key"),
        Index("ix_canonical_companies_canonical_name", "canonical_name"),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    matched_sources: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=1)
    linked_company_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    links: Mapped[list["CanonicalCompanyLink"]] = relationship(
        back_populates="canonical_company",
        cascade="all, delete-orphan",
    )


class CanonicalCompanyLink(Base):
    __tablename__ = "canonical_company_links"
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_canonical_company_links_company_id"),
        UniqueConstraint("source_type", "source_id", name="uq_canonical_company_links_source"),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    canonical_company_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("canonical_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[str] = mapped_column(String(500), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    match_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    canonical_company: Mapped[CanonicalCompany] = relationship(back_populates="links")
