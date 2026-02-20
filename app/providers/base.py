"""
Abstract payment provider interface.

All payment providers (ACH, Wire, cross-border) implement this interface.
In production, these would wrap real banking APIs (Modern Treasury, Dwolla,
Goldman Sachs TxB). Here they're mocked to demonstrate the integration pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PaymentOrderRequest:
    """Request to create a payment order."""

    payment_type: str  # "ach", "cross_border", "wire"
    subtype: Optional[str]  # e.g. "CCD", "sepa"
    amount_cents: int  # Amount in smallest currency unit
    currency: str  # ISO 4217
    direction: str = "credit"
    originating_account_id: str = "internal_usd_001"
    receiving_account_id: str = ""
    effective_date: Optional[str] = None
    description: str = ""
    statement_descriptor: str = ""
    purpose: Optional[str] = None
    fx_indicator: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class PaymentOrderResponse:
    """Response from creating a payment order."""

    payment_order_id: str
    status: str  # "pending", "processing", "completed", "failed"
    provider: str  # e.g. "mock_ach", "mock_wire"
    message: str = ""


class PaymentProvider(ABC):
    """Abstract base class for payment providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'mock_ach')."""
        ...

    @abstractmethod
    async def create_payment_order(self, request: PaymentOrderRequest) -> PaymentOrderResponse:
        """
        Submit a payment order to the provider.

        Implementations should be idempotent where possible (e.g. using
        statement_descriptor as a dedup key).

        Raises:
            ProviderError: On transient failure (will be retried).
            PermanentError: On non-retriable failure.
        """
        ...
