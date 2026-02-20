"""
Multi-rail payment routing engine.

Selects the optimal payment rail for each payout based on:
  1. Investor country
  2. Payment method preference (ACH vs Wire)
  3. External account capabilities (ABA routing = US bank)

Routing priority:
  - Foreign investor with US bank account (Wise, etc.) → domestic ACH
  - US investor → domestic ACH (CCD)
  - Supported non-US country → local cross-border rail (SEPA, BACS, etc.)
  - Unsupported country → international wire fallback (USD)

For cross-border payments, uses fixed_to_variable FX indicator so the USD
amount is fixed and the recipient gets the equivalent in local currency.
"""

from dataclasses import dataclass
from typing import Optional

from app.routing.country_rails import GLOBAL_ACH_MAP


@dataclass
class RailDecision:
    """Result of the rail selection process."""

    payment_type: str  # "ach", "cross_border", "wire"
    subtype: Optional[str]  # e.g. "CCD", "sepa", "bacs"
    currency: str  # ISO 4217 currency for the payment order
    purpose: Optional[str]  # Purpose code (e.g. CPA "250" for Canada)
    fx_indicator: Optional[str]  # "fixed_to_variable" for cross-border
    label: str  # Human-readable: "ACH (US)", "Cross-Border SEPA", "Wire (International)"

    @property
    def is_cross_border(self) -> bool:
        return self.payment_type == "cross_border"


def select_rail(
    country_code: Optional[str],
    payment_method: Optional[str] = None,
    has_aba_routing: bool = False,
) -> RailDecision:
    """
    Select the optimal payment rail for a payout.

    Args:
        country_code: ISO 3166-1 alpha-2 country code of the investor.
        payment_method: Preferred method ("ACH" or "Wire"). Used as hint, not binding.
        has_aba_routing: True if the external account has ABA routing (US bank).
            This allows foreign investors with US bank accounts (e.g. Wise,
            Mercury) to receive domestic ACH instead of costly cross-border.

    Returns:
        RailDecision with the selected payment type, currency, and metadata.
    """
    country = (country_code or "").strip().upper()

    # Priority 1: Foreign investor with US bank account → domestic ACH
    # This handles Wise, Mercury, and similar multi-currency account providers
    if has_aba_routing and country != "US":
        return RailDecision(
            payment_type="ach",
            subtype="CCD",
            currency="USD",
            purpose=None,
            fx_indicator=None,
            label=f"ACH (US) — foreign investor ({country}) with US bank",
        )

    # Priority 2: US investor → domestic ACH
    if country == "US":
        return RailDecision(
            payment_type="ach",
            subtype="CCD",
            currency="USD",
            purpose=None,
            fx_indicator=None,
            label="ACH (US)",
        )

    # Priority 3: Supported cross-border country → local rail
    cfg = GLOBAL_ACH_MAP.get(country)
    if cfg:
        subtype = cfg["subtype"]
        currency = cfg.get("currency", "USD")
        return RailDecision(
            payment_type="cross_border",
            subtype=subtype,
            currency=currency,
            purpose=cfg.get("purpose"),
            fx_indicator="fixed_to_variable",
            label=f"Cross-Border {subtype.upper()} ({currency})",
        )

    # Fallback: International wire (USD)
    return RailDecision(
        payment_type="wire",
        subtype=None,
        currency="USD",
        purpose=None,
        fx_indicator=None,
        label=f"Wire (International) — {country or 'unknown'}",
    )
