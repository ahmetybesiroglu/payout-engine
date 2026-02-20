"""
Immutable audit trail for payment operations.

Every state change gets an append-only audit log entry with:
  - Run ID (which orchestrator run triggered it)
  - Payout ID (which specific payout)
  - Action (what happened)
  - Details (context, error messages, routing decisions)
  - Timestamp (UTC)

These records are never modified or deleted — critical for financial
compliance and operational debugging.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payout import AuditLog

logger = logging.getLogger("payout_engine.audit")


async def log_event(
    session: AsyncSession,
    action: str,
    run_id: Optional[str] = None,
    payout_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """
    Create an immutable audit log entry.

    Args:
        session: Database session.
        action: What happened (e.g. "eligibility_check", "rail_selected", "payment_created").
        run_id: The orchestrator run that triggered this event.
        payout_id: The specific payout this event relates to.
        details: Arbitrary context (serialized to JSON).

    Returns:
        The created AuditLog record.
    """
    entry = AuditLog(
        run_id=run_id,
        payout_id=payout_id,
        action=action,
        details=json.dumps(details) if details else None,
        timestamp=datetime.now(timezone.utc),
    )
    session.add(entry)
    logger.info(
        "AUDIT | run=%s payout=%s action=%s | %s",
        run_id or "-",
        payout_id or "-",
        action,
        json.dumps(details)[:200] if details else "",
    )
    return entry


def append_note(existing_notes: Optional[str], message: str) -> str:
    """
    Append a timestamped note to a payout's notes field.

    Follows the production pattern of building a running log of
    significant events on each payment record for CX visibility.
    """
    prefix = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] "
    new_note = prefix + message
    if not existing_notes:
        return new_note
    return f"{existing_notes}\n{new_note}"
