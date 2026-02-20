"""Enumerations for the payout engine domain model."""

from enum import Enum


class PayoutStatus(str, Enum):
    """Lifecycle states for an individual payout."""

    PENDING = "pending"
    ELIGIBLE = "eligible"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStatus(str, Enum):
    """Lifecycle states for a payout run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PaymentRail(str, Enum):
    """Supported payment rails."""

    ACH = "ach"
    WIRE = "wire"
    SEPA = "sepa"
    BACS = "bacs"
    EFT = "eft"
    SIC = "sic"
    AU_BECS = "au_becs"
    SG_GIRO = "sg_giro"
    NEFT = "neft"
    ZENGIN = "zengin"
    DK_NETS = "dk_nets"
    NZ_BECS = "nz_becs"
    NICS = "nics"
    CHATS = "chats"
    SE_BANKGIROT = "se_bankgirot"
    RO_SENT = "ro_sent"
    MX_CCEN = "mx_ccen"
    MASAV = "masav"
    SKNBI = "sknbi"
    HU_ICS = "hu_ics"
    PL_ELIXIR = "pl_elixir"


class SkipReason(str, Enum):
    """Categorized reasons for skipping a payout."""

    INVALID_METHOD = "invalid_method"
    WRONG_STATUS = "wrong_status"
    INVALID_AMOUNT = "invalid_amount"
    MISSING_EXTERNAL_ACCOUNT = "missing_external_account"
    EXISTING_PAYMENT_ORDER = "existing_payment_order"
    MISSING_COUNTRY = "missing_country"
