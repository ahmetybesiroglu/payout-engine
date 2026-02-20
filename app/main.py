"""
Payout Engine — Multi-Rail Payout Orchestration API.

A production-grade payout orchestration engine that routes investor payments
across 30+ countries through optimal payment rails (ACH, SEPA, BACS, Zengin,
GIRO, and more).

Start the server:
    uvicorn app.main:app --reload

Or with Docker:
    docker-compose up
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.payouts import router as payouts_router
from app.api.runs import router as runs_router
from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="Payout Engine",
    description=(
        "Multi-rail payout orchestration engine for cross-border investor payments. "
        "Routes payouts across 30+ countries through optimal payment rails with "
        "idempotent execution, categorized exception handling, and immutable audit trails."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(runs_router, prefix="/api")
app.include_router(payouts_router, prefix="/api")
