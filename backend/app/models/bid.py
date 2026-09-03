from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Bid(Base):
    """Individual bid submitted against a tender.

    Represents a single bidder's participation in a procurement. This is
    distinct from Award (winner) — a tender may have many bids but only
    one or a few awards.

    Currently sourced from Prozorro (Ukraine open-contracting data).
    Indian procurement sources (CPPP, GeM, state portals) do NOT expose
    individual bid records; bidder_count for Indian tenders is unavailable
    until those connectors are extended.

    Fields follow the OCDS (Open Contracting Data Standard) structure that
    Prozorro publishes.
    """

    __tablename__ = "bids"
    __table_args__ = (
        UniqueConstraint("tender_id", "source_bid_id", name="uq_bids_tender_source_bid"),
        Index("ix_bids_tender_id", "tender_id"),
        Index("ix_bids_company_id", "company_id"),
        Index("ix_bids_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Tender relationship (required)
    tender_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Company/bidder relationship (nullable — identity resolution may not succeed)
    company_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Source bid identifier (e.g. Prozorro bid UUID)
    source_bid_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Bidder identity (preserved even if company_id resolution fails)
    bidder_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bidder_registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Bid status: active | unsuccessful | disqualified | invalid | draft
    # NULL when source does not provide status
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Whether this bid was responsive (eligible for award consideration)
    # NULL = unknown (source does not expose this)
    responsive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Whether this bid was withdrawn before evaluation
    withdrawn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Bid amount and currency (per-lot value in OCDS)
    bid_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UAH")

    # Submission timestamp (OCDS submissionDate)
    submission_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Provenance
    source_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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

    tender: Mapped["Tender"] = relationship(back_populates="bids")
    company: Mapped["Company | None"] = relationship()
