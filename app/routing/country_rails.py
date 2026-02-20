"""
Country-specific payment rail configuration.

Maps ISO 3166-1 alpha-2 country codes to their optimal local payment rail,
currency, and any required purpose codes. This enables automatic routing of
cross-border payouts through the cheapest and fastest available rail for each
destination country.

Coverage: 30+ countries across SEPA, BACS, EFT, SIC, Zengin, GIRO, CHATS,
BECS, NEFT, ELIXIR, and more.
"""

from typing import TypedDict, Optional


class RailConfig(TypedDict, total=False):
    """Configuration for a country-specific payment rail."""

    type: str  # "ach", "cross_border", "wire"
    subtype: str  # Rail-specific identifier (e.g. "sepa", "bacs")
    currency: str  # ISO 4217 currency code
    purpose: Optional[str]  # Purpose code (required by some rails, e.g. CPA for Canada)


GLOBAL_ACH_MAP: dict[str, RailConfig] = {
    # ─── SEPA Zone (EUR) ───────────────────────────────────────────────
    # Single Euro Payments Area — covers 19 Eurozone countries.
    # Uses IBAN-only routing. No SWIFT/BIC required.
    "DE": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Germany
    "FR": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # France
    "ES": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Spain
    "NL": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Netherlands
    "IT": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Italy
    "AT": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Austria
    "BE": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Belgium
    "IE": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Ireland
    "PT": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Portugal
    "FI": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Finland
    "GR": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Greece
    "LU": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Luxembourg
    "CY": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Cyprus
    "MT": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Malta
    "SK": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Slovakia
    "LT": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Lithuania
    "SI": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Slovenia
    "EE": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Estonia
    "LV": {"type": "cross_border", "subtype": "sepa", "currency": "EUR"},  # Latvia
    # ─── UK (GBP) ──────────────────────────────────────────────────────
    # Bankers' Automated Clearing Services — sort code + account number.
    "GB": {"type": "cross_border", "subtype": "bacs", "currency": "GBP"},
    # ─── Canada (CAD) ──────────────────────────────────────────────────
    # Electronic Funds Transfer — requires CPA purpose code 250 (misc).
    "CA": {"type": "cross_border", "subtype": "eft", "currency": "CAD", "purpose": "250"},
    # ─── Switzerland (CHF) ─────────────────────────────────────────────
    # Swiss Interbank Clearing — IBAN + SWIFT required.
    "CH": {"type": "cross_border", "subtype": "sic", "currency": "CHF"},
    # ─── Poland (PLN) ──────────────────────────────────────────────────
    # ELIXIR — Polish interbank clearing system.
    "PL": {"type": "cross_border", "subtype": "pl_elixir", "currency": "PLN"},
    # ─── Australia (AUD) ───────────────────────────────────────────────
    # Bulk Electronic Clearing System — BSB + account number, SWIFT routing.
    "AU": {"type": "cross_border", "subtype": "au_becs", "currency": "AUD"},
    # ─── Singapore (SGD) ───────────────────────────────────────────────
    # General Interbank Recurring Order — SWIFT required.
    "SG": {"type": "cross_border", "subtype": "sg_giro", "currency": "SGD"},
    # ─── India (INR) ───────────────────────────────────────────────────
    # National Electronic Funds Transfer — IFSC code, FETERS purpose codes.
    "IN": {"type": "cross_border", "subtype": "neft", "currency": "INR"},
    # ─── Japan (JPY) ───────────────────────────────────────────────────
    # Zengin System — SWIFT required, ISO purpose codes.
    "JP": {"type": "cross_border", "subtype": "zengin", "currency": "JPY"},
    # ─── Denmark (DKK) ─────────────────────────────────────────────────
    # Danish Interbank Clearing via Nets.
    "DK": {"type": "cross_border", "subtype": "dk_nets", "currency": "DKK"},
    # ─── New Zealand (NZD) ─────────────────────────────────────────────
    # NZ Bulk Electronic Clearing System — SWIFT required.
    "NZ": {"type": "cross_border", "subtype": "nz_becs", "currency": "NZD"},
    # ─── Norway (NOK) ──────────────────────────────────────────────────
    # Norwegian Interbank Clearing System — IBAN + SWIFT.
    "NO": {"type": "cross_border", "subtype": "nics", "currency": "NOK"},
    # ─── Hong Kong (HKD) ──────────────────────────────────────────────
    # Clearing House Automated Transfer System.
    "HK": {"type": "cross_border", "subtype": "chats", "currency": "HKD"},
    # ─── Sweden (SEK) ──────────────────────────────────────────────────
    # Swedish Bankgirot — SWIFT required.
    "SE": {"type": "cross_border", "subtype": "se_bankgirot", "currency": "SEK"},
    # ─── Romania (RON) ─────────────────────────────────────────────────
    # SENT — Romanian interbank clearing. IBAN + SWIFT required.
    "RO": {"type": "cross_border", "subtype": "ro_sent", "currency": "RON"},
    # ─── Mexico (MXN) ──────────────────────────────────────────────────
    # CCEN (SPEI) — requires 18-digit CLABE number.
    "MX": {"type": "cross_border", "subtype": "mx_ccen", "currency": "MXN"},
    # ─── Israel (ILS) ──────────────────────────────────────────────────
    # MASAV — Israeli automated banking system. IBAN + SWIFT.
    "IL": {"type": "cross_border", "subtype": "masav", "currency": "ILS"},
    # ─── Indonesia (IDR) ───────────────────────────────────────────────
    # SKNBI — Indonesian clearing system. SKNBI code required.
    "ID": {"type": "cross_border", "subtype": "sknbi", "currency": "IDR"},
    # ─── Hungary (HUF) ─────────────────────────────────────────────────
    # Hungarian Interbank Clearing System.
    "HU": {"type": "cross_border", "subtype": "hu_ics", "currency": "HUF"},
}


# Convenience set of all supported destination countries
SUPPORTED_COUNTRIES = {"US"} | set(GLOBAL_ACH_MAP.keys())
