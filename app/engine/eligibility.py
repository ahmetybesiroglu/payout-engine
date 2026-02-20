"""
Payment eligibility checks with categorized skip reasons.

Before routing and executing a payout, we verify:
  1. Payment method is valid (ACH or Wire)
  2. Amount is positive
  3. External bank account exists
  4. Country is present
  5. No duplicate payment order (idempotency guard)

Each check returns a structured result so the orchestrator can track
skip reasons by category — critical for operational reporting.
"""

from dataclasses import dataclass
from typing import Optional

from app.models.enums import SkipReason


ALLOWED_METHODS = {"ACH", "Wire"}


@dataclass
class EligibilityResult:
    """Result of an eligibility check."""

    eligible: bool
    skip_reason: Optional[SkipReason] = None
    message: str = ""


def check_eligibility(
    payment_method: Optional[str],
    amount: Optional[float],
    external_account_id: Optional[str],
    country: Optional[str],
    existing_payment_order_id: Optional[str] = None,
) -> EligibilityResult:
    """
    Check whether a payout is eligible for processing.

    Args:
        payment_method: Investor's payment method preference ("ACH" or "Wire").
        amount: Payout amount in USD.
        external_account_id: The investor's bank account identifier.
        country: ISO 3166-1 alpha-2 country code.
        existing_payment_order_id: If set, payout was already processed.

    Returns:
        EligibilityResult indicating pass/fail with categorized reason.
    """
    # Idempotency: already has a payment order
    if existing_payment_order_id:
        return EligibilityResult(
            eligible=False,
            skip_reason=SkipReason.EXISTING_PAYMENT_ORDER,
            message=f"Payment order already exists: {existing_payment_order_id}",
        )

    # Valid payment method
    if not payment_method or payment_method not in ALLOWED_METHODS:
        return EligibilityResult(
            eligible=False,
            skip_reason=SkipReason.INVALID_METHOD,
            message=f"Invalid payment method: {payment_method}",
        )

    # Positive amount
    if amount is None or amount <= 0:
        return EligibilityResult(
            eligible=False,
            skip_reason=SkipReason.INVALID_AMOUNT,
            message=f"Invalid amount: {amount}",
        )

    # External account required
    if not external_account_id:
        return EligibilityResult(
            eligible=False,
            skip_reason=SkipReason.MISSING_EXTERNAL_ACCOUNT,
            message="No external bank account on file",
        )

    # Country required for routing
    if not country:
        return EligibilityResult(
            eligible=False,
            skip_reason=SkipReason.MISSING_COUNTRY,
            message="Missing country code",
        )

    return EligibilityResult(eligible=True)
