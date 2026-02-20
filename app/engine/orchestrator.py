"""
Payout orchestrator — the core execution engine.

Processes all eligible payouts for a liquidation event in a single
idempotent run. The flow for each payout:

  1. Eligibility check (method, amount, account, country, dedup)
  2. Rail selection (country → optimal rail)
  3. Provider execution (create payment order via banking API)
  4. Audit logging (every state change recorded)

Idempotency guarantees:
  - Each (liquidation_event_id, investor_id) pair can only have one payout
  - Payouts with existing payment_order_id are skipped
  - Re-running the same event produces zero new payment orders

Inspired by a production system that processes 1,000+ investor payouts
across 30+ countries, reducing processing time from ~40 hours to ~15 minutes.
"""

import json
import logging
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import append_note, log_event
from app.engine.eligibility import check_eligibility
from app.engine.retry import PermanentError, ProviderError, with_retry
from app.models.enums import PayoutStatus, RunStatus, SkipReason
from app.models.payout import AuditLog, Investor, LiquidationEvent, Payout, PayoutRun
from app.providers.base import PaymentOrderRequest, PaymentProvider
from app.routing.rail_selector import select_rail

logger = logging.getLogger("payout_engine.orchestrator")


def _cents(amount: float) -> int:
    """Convert dollar amount to cents, avoiding floating point issues."""
    return int(round(amount * 100))


async def execute_run(
    session: AsyncSession,
    liquidation_event_id: str,
    provider: PaymentProvider,
) -> PayoutRun:
    """
    Execute a full payout run for a liquidation event.

    This is the main entry point for the orchestrator. It:
      1. Creates a PayoutRun record
      2. Loads or creates Payout records for all investors in the event
      3. Processes each eligible payout (eligibility → routing → execution)
      4. Updates run summary with categorized counts

    Args:
        session: Database session.
        liquidation_event_id: The event to process.
        provider: Payment provider implementation.

    Returns:
        The completed PayoutRun with summary statistics.
    """
    # Create run record
    run = PayoutRun(
        id=str(uuid.uuid4()),
        liquidation_event_id=liquidation_event_id,
        status=RunStatus.RUNNING.value,
    )
    session.add(run)
    await session.flush()

    await log_event(session, "run_started", run_id=run.id, details={
        "liquidation_event_id": liquidation_event_id,
    })

    # Load the liquidation event
    event = await session.get(LiquidationEvent, liquidation_event_id)
    if not event:
        run.status = RunStatus.FAILED.value
        run.completed_at = datetime.now(timezone.utc)
        await log_event(session, "run_failed", run_id=run.id, details={
            "error": f"Liquidation event not found: {liquidation_event_id}",
        })
        await session.commit()
        return run

    # Load existing payouts for this event (may have been created by a previous seed/run)
    existing_payouts_result = await session.execute(
        select(Payout).where(Payout.liquidation_event_id == liquidation_event_id)
    )
    existing_payouts = {p.investor_id: p for p in existing_payouts_result.scalars().all()}

    # Load investors
    investors_result = await session.execute(select(Investor))
    investors = investors_result.scalars().all()

    # Ensure a Payout record exists for each investor
    payouts: list[Payout] = []
    for inv in investors:
        if inv.id in existing_payouts:
            payout = existing_payouts[inv.id]
            # Associate with this run if not already completed
            if payout.status not in (PayoutStatus.COMPLETED.value, PayoutStatus.SKIPPED.value):
                payout.run_id = run.id
        else:
            # Create new payout
            share = event.total_amount / max(len(investors), 1)
            payout = Payout(
                run_id=run.id,
                liquidation_event_id=liquidation_event_id,
                investor_id=inv.id,
                investor_name=inv.name,
                amount=round(share, 2),
                currency="USD",
                country=inv.country,
                payment_method=inv.payment_method,
                has_aba_routing=inv.has_aba_routing,
                external_account_id=inv.external_account_id,
                status=PayoutStatus.PENDING.value,
            )
            session.add(payout)

        payouts.append(payout)

    await session.flush()

    logger.info(
        "Run %s: processing %d payouts for event %s",
        run.id[:8],
        len(payouts),
        liquidation_event_id,
    )

    # Process each payout
    skip_counts: Counter[str] = Counter()
    successes = 0
    skipped = 0
    failures = 0

    for payout in payouts:
        result = await _process_single_payout(session, run, payout, provider, event)
        if result == "created":
            successes += 1
        elif result == "skipped":
            skipped += 1
            if payout.skip_reason:
                skip_counts[payout.skip_reason] += 1
        elif result == "failed":
            failures += 1

    # Update run summary
    run.created_count = successes
    run.skipped_count = skipped
    run.failed_count = failures
    run.skip_breakdown = json.dumps(dict(skip_counts)) if skip_counts else None
    run.status = RunStatus.COMPLETED.value
    run.completed_at = datetime.now(timezone.utc)

    await log_event(session, "run_completed", run_id=run.id, details={
        "created": successes,
        "skipped": skipped,
        "failed": failures,
        "skip_breakdown": dict(skip_counts),
    })

    logger.info(
        "Run %s summary: created=%d, skipped=%d (%s), failed=%d",
        run.id[:8],
        successes,
        skipped,
        ", ".join(f"{k}={v}" for k, v in skip_counts.items()) or "none",
        failures,
    )

    await session.commit()
    return run


async def _process_single_payout(
    session: AsyncSession,
    run: PayoutRun,
    payout: Payout,
    provider: PaymentProvider,
    event: LiquidationEvent,
) -> str:
    """
    Process a single payout through eligibility → routing → execution.

    Returns: "created", "skipped", or "failed"
    """
    # Step 1: Eligibility check
    result = check_eligibility(
        payment_method=payout.payment_method,
        amount=payout.amount,
        external_account_id=payout.external_account_id,
        country=payout.country,
        existing_payment_order_id=payout.payment_order_id,
    )

    if not result.eligible:
        payout.status = PayoutStatus.SKIPPED.value
        payout.skip_reason = result.skip_reason.value if result.skip_reason else None
        payout.notes = append_note(payout.notes, f"Skipped: {result.message}")

        await log_event(session, "eligibility_failed", run_id=run.id, payout_id=payout.id, details={
            "reason": result.skip_reason.value if result.skip_reason else "unknown",
            "message": result.message,
        })
        return "skipped"

    # Step 2: Rail selection
    rail = select_rail(
        country_code=payout.country,
        payment_method=payout.payment_method,
        has_aba_routing=bool(payout.has_aba_routing),
    )
    payout.rail = rail.subtype or rail.payment_type
    payout.rail_subtype = rail.subtype
    payout.rail_currency = rail.currency
    payout.fx_indicator = rail.fx_indicator
    payout.payment_order_type = rail.label

    await log_event(session, "rail_selected", run_id=run.id, payout_id=payout.id, details={
        "country": payout.country,
        "rail": rail.payment_type,
        "subtype": rail.subtype,
        "currency": rail.currency,
        "fx": rail.fx_indicator,
        "label": rail.label,
    })

    # Step 3: Create payment order via provider
    request = PaymentOrderRequest(
        payment_type=rail.payment_type,
        subtype=rail.subtype,
        amount_cents=_cents(payout.amount),
        currency=rail.currency,
        receiving_account_id=payout.external_account_id or "",
        effective_date=event.payout_date,
        description=f"Payout to {payout.investor_name or payout.investor_id}",
        statement_descriptor=payout.investor_id[:10],
        purpose=rail.purpose,
        fx_indicator=rail.fx_indicator,
        metadata={
            "event_id": payout.liquidation_event_id,
            "investor_id": payout.investor_id,
            "country": payout.country or "",
        },
    )

    try:
        payout.status = PayoutStatus.PROCESSING.value
        response = await with_retry(provider.create_payment_order, request)

        payout.payment_order_id = response.payment_order_id
        payout.status = PayoutStatus.COMPLETED.value
        payout.notes = append_note(payout.notes, f"Payment order created: {response.payment_order_id}")

        await log_event(session, "payment_created", run_id=run.id, payout_id=payout.id, details={
            "payment_order_id": response.payment_order_id,
            "provider": response.provider,
            "type": rail.payment_type,
            "currency": rail.currency,
            "amount": payout.amount,
        })
        return "created"

    except PermanentError as e:
        payout.status = PayoutStatus.FAILED.value
        payout.notes = append_note(payout.notes, f"Permanent failure: {e}")
        await log_event(session, "payment_failed_permanent", run_id=run.id, payout_id=payout.id, details={
            "error": str(e),
            "status_code": e.status_code,
        })
        return "failed"

    except ProviderError as e:
        payout.status = PayoutStatus.FAILED.value
        payout.notes = append_note(payout.notes, f"Provider error after retries: {e}")
        await log_event(session, "payment_failed_retries_exhausted", run_id=run.id, payout_id=payout.id, details={
            "error": str(e),
            "status_code": e.status_code,
        })
        return "failed"

    except Exception as e:
        payout.status = PayoutStatus.FAILED.value
        payout.notes = append_note(payout.notes, f"Unexpected error: {e}")
        await log_event(session, "payment_failed_unexpected", run_id=run.id, payout_id=payout.id, details={
            "error": str(e),
        })
        return "failed"
