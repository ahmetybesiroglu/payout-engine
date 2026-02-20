"""
Payout run endpoints.

POST /runs  — Trigger a new payout run for a liquidation event.
GET  /runs  — List all runs with summary stats.
GET  /runs/{run_id} — Get detailed run status with per-payout breakdown.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.engine.orchestrator import execute_run
from app.models.payout import Payout, PayoutRun
from app.providers.mock_provider import MockPaymentProvider

router = APIRouter(prefix="/runs", tags=["runs"])


class RunRequest(BaseModel):
    liquidation_event_id: str


class PayoutSummary(BaseModel):
    id: str
    investor_id: str
    investor_name: Optional[str]
    amount: float
    currency: str
    country: Optional[str]
    rail: Optional[str]
    payment_order_type: Optional[str]
    status: str
    skip_reason: Optional[str]
    payment_order_id: Optional[str]

    model_config = {"from_attributes": True}


class RunResponse(BaseModel):
    id: str
    liquidation_event_id: str
    status: str
    created_count: int
    skipped_count: int
    failed_count: int
    skip_breakdown: Optional[dict] = None
    started_at: Optional[str]
    completed_at: Optional[str]
    payouts: Optional[list[PayoutSummary]] = None

    model_config = {"from_attributes": True}


def _run_to_response(
    run: PayoutRun,
    payouts_list: list[Payout] | None = None,
) -> RunResponse:
    skip_bd = None
    if run.skip_breakdown:
        try:
            skip_bd = json.loads(run.skip_breakdown)
        except (json.JSONDecodeError, TypeError):
            pass

    payouts = None
    if payouts_list is not None:
        payouts = [
            PayoutSummary(
                id=p.id,
                investor_id=p.investor_id,
                investor_name=p.investor_name,
                amount=p.amount,
                currency=p.currency,
                country=p.country,
                rail=p.rail,
                payment_order_type=p.payment_order_type,
                status=p.status,
                skip_reason=p.skip_reason,
                payment_order_id=p.payment_order_id,
            )
            for p in payouts_list
        ]

    return RunResponse(
        id=run.id,
        liquidation_event_id=run.liquidation_event_id,
        status=run.status,
        created_count=run.created_count or 0,
        skipped_count=run.skipped_count or 0,
        failed_count=run.failed_count or 0,
        skip_breakdown=skip_bd,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        payouts=payouts,
    )


async def _load_run_payouts(session: AsyncSession, run_id: str) -> list[Payout]:
    """Explicitly load payouts for a run (avoids lazy loading issues)."""
    result = await session.execute(
        select(Payout).where(Payout.run_id == run_id).order_by(Payout.investor_id)
    )
    return list(result.scalars().all())


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(body: RunRequest, session: AsyncSession = Depends(get_session)):
    """
    Trigger a payout run for a liquidation event.

    Idempotent: re-running the same event will skip already-processed payouts,
    resulting in 0 new payment orders if all were previously completed.
    """
    provider = MockPaymentProvider()
    run = await execute_run(session, body.liquidation_event_id, provider)
    payouts = await _load_run_payouts(session, run.id)
    return _run_to_response(run, payouts_list=payouts)


@router.get("", response_model=list[RunResponse])
async def list_runs(session: AsyncSession = Depends(get_session)):
    """List all payout runs with summary statistics."""
    result = await session.execute(
        select(PayoutRun).order_by(PayoutRun.started_at.desc())
    )
    runs = result.scalars().all()
    return [_run_to_response(r) for r in runs]


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)):
    """Get detailed run status including per-payout breakdown."""
    run = await session.get(PayoutRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    payouts = await _load_run_payouts(session, run_id)
    return _run_to_response(run, payouts_list=payouts)
