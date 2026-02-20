"""Integration tests for the payout orchestrator."""

import pytest
from sqlalchemy import select

from app.engine.orchestrator import execute_run
from app.models.payout import AuditLog, Payout, PayoutRun
from app.providers.mock_provider import MockPaymentProvider


@pytest.mark.asyncio
async def test_full_run(seeded_session):
    """Execute a full payout run and verify results."""
    provider = MockPaymentProvider(failure_rate=0.0, latency_ms=0)
    run = await execute_run(seeded_session, "LIQ-TEST-001", provider)

    assert run.status == "completed"
    assert run.created_count > 0
    assert run.skipped_count > 0  # Ghost Investor + Crypto Only should be skipped
    assert run.created_count + run.skipped_count + run.failed_count == 8  # 8 investors

    # Verify specific routing
    payouts = (await seeded_session.execute(
        select(Payout).where(Payout.liquidation_event_id == "LIQ-TEST-001")
    )).scalars().all()

    payout_map = {p.investor_id: p for p in payouts}

    # US investor → ACH
    us = payout_map["INV-001"]
    assert us.status == "completed"
    assert us.rail == "CCD"
    assert us.rail_currency == "USD"

    # German investor → SEPA
    de = payout_map["INV-010"]
    assert de.status == "completed"
    assert de.rail == "sepa"
    assert de.rail_currency == "EUR"

    # UK investor → BACS
    gb = payout_map["INV-030"]
    assert gb.status == "completed"
    assert gb.rail == "bacs"
    assert gb.rail_currency == "GBP"

    # Japanese investor → Zengin
    jp = payout_map["INV-038"]
    assert jp.status == "completed"
    assert jp.rail == "zengin"
    assert jp.rail_currency == "JPY"

    # JP investor with US bank → domestic ACH
    jp_wise = payout_map["INV-050"]
    assert jp_wise.status == "completed"
    assert jp_wise.rail == "CCD"
    assert jp_wise.rail_currency == "USD"

    # UAE investor → Wire fallback
    ae = payout_map["INV-052"]
    assert ae.status == "completed"
    assert ae.rail == "wire"

    # Ghost Investor → skipped (missing external account)
    ghost = payout_map["INV-060"]
    assert ghost.status == "skipped"
    assert ghost.skip_reason == "missing_external_account"

    # Crypto Only → skipped (invalid method)
    crypto = payout_map["INV-061"]
    assert crypto.status == "skipped"
    assert crypto.skip_reason == "invalid_method"


@pytest.mark.asyncio
async def test_idempotency(seeded_session):
    """Running the same event twice should produce zero new payment orders."""
    provider = MockPaymentProvider(failure_rate=0.0, latency_ms=0)

    # First run
    run1 = await execute_run(seeded_session, "LIQ-TEST-001", provider)
    assert run1.created_count > 0

    # Second run — should skip all (already have payment orders)
    run2 = await execute_run(seeded_session, "LIQ-TEST-001", provider)
    assert run2.created_count == 0
    assert run2.skipped_count > 0


@pytest.mark.asyncio
async def test_audit_trail_created(seeded_session):
    """Every payout should have audit log entries."""
    provider = MockPaymentProvider(failure_rate=0.0, latency_ms=0)
    run = await execute_run(seeded_session, "LIQ-TEST-001", provider)

    logs = (await seeded_session.execute(
        select(AuditLog).where(AuditLog.run_id == run.id)
    )).scalars().all()

    # Should have at least: run_started, per-payout events, run_completed
    assert len(logs) >= 3

    actions = {log.action for log in logs}
    assert "run_started" in actions
    assert "run_completed" in actions
