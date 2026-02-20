"""
Payout query and trace endpoints.

GET /payouts           — List payouts with filters (status, country, rail).
GET /payouts/{id}      — Get a single payout with full details.
GET /payouts/{id}/trace — Full audit trail for a payout.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.payout import AuditLog, Payout

router = APIRouter(prefix="/payouts", tags=["payouts"])


class PayoutDetail(BaseModel):
    id: str
    run_id: Optional[str]
    liquidation_event_id: str
    investor_id: str
    investor_name: Optional[str]
    amount: float
    currency: str
    country: Optional[str]
    payment_method: Optional[str]
    has_aba_routing: bool
    rail: Optional[str]
    rail_subtype: Optional[str]
    rail_currency: Optional[str]
    fx_indicator: Optional[str]
    payment_order_type: Optional[str]
    status: str
    skip_reason: Optional[str]
    payment_order_id: Optional[str]
    notes: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    model_config = {"from_attributes": True}


class AuditEntry(BaseModel):
    id: int
    action: str
    details: Optional[dict] = None
    timestamp: Optional[str]

    model_config = {"from_attributes": True}


class PayoutTrace(BaseModel):
    payout: PayoutDetail
    audit_trail: list[AuditEntry]


def _payout_to_detail(p: Payout) -> PayoutDetail:
    return PayoutDetail(
        id=p.id,
        run_id=p.run_id,
        liquidation_event_id=p.liquidation_event_id,
        investor_id=p.investor_id,
        investor_name=p.investor_name,
        amount=p.amount,
        currency=p.currency,
        country=p.country,
        payment_method=p.payment_method,
        has_aba_routing=bool(p.has_aba_routing),
        rail=p.rail,
        rail_subtype=p.rail_subtype,
        rail_currency=p.rail_currency,
        fx_indicator=p.fx_indicator,
        payment_order_type=p.payment_order_type,
        status=p.status,
        skip_reason=p.skip_reason,
        payment_order_id=p.payment_order_id,
        notes=p.notes,
        created_at=p.created_at.isoformat() if p.created_at else None,
        updated_at=p.updated_at.isoformat() if p.updated_at else None,
    )


@router.get("", response_model=list[PayoutDetail])
async def list_payouts(
    status: Optional[str] = Query(None, description="Filter by status"),
    country: Optional[str] = Query(None, description="Filter by country code"),
    rail: Optional[str] = Query(None, description="Filter by payment rail"),
    event_id: Optional[str] = Query(None, description="Filter by liquidation event"),
    session: AsyncSession = Depends(get_session),
):
    """List payouts with optional filters."""
    stmt = select(Payout)

    if status:
        stmt = stmt.where(Payout.status == status)
    if country:
        stmt = stmt.where(Payout.country == country.upper())
    if rail:
        stmt = stmt.where(Payout.rail == rail)
    if event_id:
        stmt = stmt.where(Payout.liquidation_event_id == event_id)

    stmt = stmt.order_by(Payout.created_at.desc())
    result = await session.execute(stmt)
    return [_payout_to_detail(p) for p in result.scalars().all()]


@router.get("/{payout_id}", response_model=PayoutDetail)
async def get_payout(payout_id: str, session: AsyncSession = Depends(get_session)):
    """Get a single payout with full details."""
    payout = await session.get(Payout, payout_id)
    if not payout:
        raise HTTPException(status_code=404, detail=f"Payout not found: {payout_id}")
    return _payout_to_detail(payout)


@router.get("/{payout_id}/trace", response_model=PayoutTrace)
async def get_payout_trace(payout_id: str, session: AsyncSession = Depends(get_session)):
    """
    Full audit trail for a payout.

    Returns the payout details plus every audit log entry, ordered
    chronologically. Useful for debugging payment failures and
    understanding the routing decisions made.
    """
    payout = await session.get(Payout, payout_id)
    if not payout:
        raise HTTPException(status_code=404, detail=f"Payout not found: {payout_id}")

    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.payout_id == payout_id)
        .order_by(AuditLog.timestamp.asc())
    )
    logs = result.scalars().all()

    audit_trail = []
    for log in logs:
        details = None
        if log.details:
            try:
                details = json.loads(log.details)
            except (json.JSONDecodeError, TypeError):
                details = {"raw": log.details}

        audit_trail.append(AuditEntry(
            id=log.id,
            action=log.action,
            details=details,
            timestamp=log.timestamp.isoformat() if log.timestamp else None,
        ))

    return PayoutTrace(
        payout=_payout_to_detail(payout),
        audit_trail=audit_trail,
    )
