"""Shared test fixtures."""

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.payout import Base, Investor, LiquidationEvent


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    """Create a fresh in-memory database for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(db_session: AsyncSession):
    """Database session pre-loaded with sample investors and events."""
    investors = [
        Investor(id="INV-001", name="John Smith", country="US", payment_method="ACH", external_account_id="ext_us_001"),
        Investor(id="INV-010", name="Hans Mueller", country="DE", payment_method="ACH", external_account_id="ext_de_001"),
        Investor(id="INV-030", name="James Thompson", country="GB", payment_method="ACH", external_account_id="ext_gb_001"),
        Investor(id="INV-038", name="Yuki Tanaka", country="JP", payment_method="ACH", external_account_id="ext_jp_001"),
        Investor(id="INV-050", name="Kenji Watanabe", country="JP", payment_method="ACH", external_account_id="ext_jp_wise", has_aba_routing=1),
        Investor(id="INV-052", name="Omar Al-Rashid", country="AE", payment_method="Wire", external_account_id="ext_ae_001"),
        Investor(id="INV-060", name="Ghost Investor", country="US", payment_method="ACH", external_account_id=None),
        Investor(id="INV-061", name="Crypto Only", country="US", payment_method="Crypto", external_account_id="ext_c_001"),
    ]
    for inv in investors:
        db_session.add(inv)

    event = LiquidationEvent(
        id="LIQ-TEST-001",
        name="Test Liquidation",
        total_amount=800_000.00,
        payout_date="2024-12-15",
    )
    db_session.add(event)
    await db_session.commit()

    yield db_session
