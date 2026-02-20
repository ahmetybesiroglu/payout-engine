"""
Mock payment provider for demonstration.

Simulates real banking API behavior:
  - Configurable latency (default 100ms)
  - Configurable failure rate (default 5%)
  - Rate limiting simulation (429s)
  - Realistic payment order IDs

In production, this would be replaced by adapters for Modern Treasury,
Dwolla, Goldman Sachs TxB, etc.
"""

import asyncio
import random
import uuid
from typing import Optional

from app.config import settings
from app.engine.retry import PermanentError, ProviderError, RateLimitError
from app.providers.base import PaymentOrderRequest, PaymentOrderResponse, PaymentProvider


class MockPaymentProvider(PaymentProvider):
    """
    Unified mock provider that handles ACH, wire, and cross-border payments.

    Simulates realistic banking API behavior including latency, transient
    failures, and rate limiting.
    """

    def __init__(
        self,
        failure_rate: Optional[float] = None,
        latency_ms: Optional[int] = None,
    ):
        self._failure_rate = failure_rate if failure_rate is not None else settings.mock_failure_rate
        self._latency_ms = latency_ms if latency_ms is not None else settings.mock_latency_ms

    @property
    def name(self) -> str:
        return "mock_provider"

    async def create_payment_order(self, request: PaymentOrderRequest) -> PaymentOrderResponse:
        # Simulate network latency
        if self._latency_ms > 0:
            jitter = random.uniform(0.5, 1.5)
            await asyncio.sleep(self._latency_ms * jitter / 1000)

        # Simulate random failures
        roll = random.random()

        if roll < self._failure_rate * 0.3:
            # Rate limit (retriable)
            raise RateLimitError(
                message="Mock rate limit — too many requests",
                retry_after=1.0,
            )

        if roll < self._failure_rate * 0.6:
            # Transient server error (retriable)
            raise ProviderError(
                message="Mock transient error — service temporarily unavailable",
                status_code=503,
                retriable=True,
            )

        if roll < self._failure_rate:
            # Permanent failure (not retriable)
            raise PermanentError(
                message="Mock permanent error — invalid account details",
                status_code=400,
            )

        # Success — generate a realistic payment order ID
        po_id = f"po_{request.payment_type}_{uuid.uuid4().hex[:16]}"

        return PaymentOrderResponse(
            payment_order_id=po_id,
            status="pending",
            provider=self.name,
            message=f"{request.payment_type.upper()} payment order created "
            f"({request.currency} {request.amount_cents / 100:.2f})",
        )
