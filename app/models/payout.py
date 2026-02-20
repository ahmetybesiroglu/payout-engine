"""SQLAlchemy models for the payout engine."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class PayoutRun(Base):
    """
    A single execution run of the payout orchestrator.

    Each run processes all eligible payouts for a given liquidation event.
    Runs are idempotent — re-triggering the same event skips already-processed payouts.
    """

    __tablename__ = "payout_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    liquidation_event_id = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="running")
    created_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skip_breakdown = Column(Text, nullable=True)  # JSON: {"invalid_method": 3, ...}
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    payouts = relationship("Payout", back_populates="run", lazy="raise")


class Payout(Base):
    """
    An individual investor payout within a run.

    Tracks the full lifecycle: eligibility check → rail selection → provider
    execution → completion/failure. The payment_order_id field prevents
    duplicate payments (idempotency key).
    """

    __tablename__ = "payouts"
    __table_args__ = (
        UniqueConstraint("liquidation_event_id", "investor_id", name="uq_event_investor"),
    )

    id = Column(String(12), primary_key=True, default=_new_id)
    run_id = Column(String(36), ForeignKey("payout_runs.id"), nullable=True)
    liquidation_event_id = Column(String(100), nullable=False, index=True)
    investor_id = Column(String(50), nullable=False, index=True)
    investor_name = Column(String(200), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    country = Column(String(2), nullable=True)
    payment_method = Column(String(20), nullable=True)  # ACH, Wire
    has_aba_routing = Column(Integer, default=0)  # 1 if foreign investor w/ US bank (Wise etc.)
    external_account_id = Column(String(100), nullable=True)

    # Routing result
    rail = Column(String(30), nullable=True)  # e.g. "sepa", "bacs", "ach"
    rail_subtype = Column(String(30), nullable=True)
    rail_currency = Column(String(3), nullable=True)
    fx_indicator = Column(String(30), nullable=True)  # "fixed_to_variable" for cross-border

    # Execution result
    status = Column(String(20), nullable=False, default="pending")
    skip_reason = Column(String(50), nullable=True)
    payment_order_id = Column(String(100), nullable=True, unique=True)
    payment_order_type = Column(String(50), nullable=True)  # "ACH (US)", "Cross-Border", "Wire"
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    run = relationship("PayoutRun", back_populates="payouts")
    audit_logs = relationship("AuditLog", back_populates="payout", lazy="raise")


class AuditLog(Base):
    """
    Immutable audit trail entry.

    Every state change — eligibility check, routing decision, provider call,
    success/failure — gets an audit log entry. These are append-only and
    never modified.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payout_id = Column(String(12), ForeignKey("payouts.id"), nullable=True, index=True)
    run_id = Column(String(36), ForeignKey("payout_runs.id"), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)

    payout = relationship("Payout", back_populates="audit_logs")


class Investor(Base):
    """Sample investor for demo/seed data."""

    __tablename__ = "investors"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    country = Column(String(2), nullable=True)
    payment_method = Column(String(20), default="ACH")
    external_account_id = Column(String(100), nullable=True)
    has_aba_routing = Column(Integer, default=0)


class LiquidationEvent(Base):
    """A liquidation event that triggers payouts."""

    __tablename__ = "liquidation_events"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    total_amount = Column(Float, nullable=False)
    payout_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
