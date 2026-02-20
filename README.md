# Payout Engine

**Multi-rail payout orchestration for cross-border investor payments.**

A production-grade payout orchestration engine that routes investor payments across **30+ countries** through optimal payment rails — ACH, SEPA, BACS, Zengin, GIRO, CHATS, and more. Built with idempotent execution, categorized exception handling, and immutable audit trails.

> Inspired by a production system processing 1,000+ investor payouts across 30+ countries at a $1B+ AUM alternative investment platform. That system reduced payout processing from **~40 hours to ~15 minutes** with a **94% day-1 completion rate**.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          FastAPI (REST)                               │
│   POST /api/runs          GET /api/payouts         GET /health       │
│   GET  /api/runs/{id}     GET /api/payouts/{id}/trace                │
└──────────┬───────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Payout Orchestrator                            │
│                                                                      │
│   For each investor payout:                                          │
│   ┌─────────────┐   ┌──────────────┐   ┌─────────────────────────┐  │
│   │ Eligibility  │──▶│ Rail Selector │──▶│ Payment Provider (Mock) │  │
│   │    Check     │   │ (30+ routes) │   │  ACH / Wire / X-Border  │  │
│   └─────────────┘   └──────────────┘   └─────────────────────────┘  │
│          │                  │                       │                 │
│          ▼                  ▼                       ▼                 │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │              Immutable Audit Trail (SQLite)                   │   │
│   │   Every state change logged: eligibility, routing, execution │   │
│   └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

## Key Design Patterns

### Multi-Rail Routing (30+ Countries)

The engine selects the optimal payment rail per country. Cross-border payments use `fixed_to_variable` FX so the USD amount is fixed and the recipient receives the equivalent in local currency.

```
Routing Priority:
├── Foreign investor with US bank (Wise/Mercury) → Domestic ACH (CCD)
├── US investor → Domestic ACH (CCD)
├── Supported country → Local rail (SEPA, BACS, EFT, Zengin, ...)
└── Unsupported country → International Wire fallback (USD)
```

| Region | Countries | Rail | Currency |
|--------|-----------|------|----------|
| SEPA Zone | DE, FR, ES, NL, IT, AT, BE, IE, PT, FI, GR, LU, CY, MT, SK, LT, SI, EE, LV | SEPA | EUR |
| United Kingdom | GB | BACS | GBP |
| Canada | CA | EFT | CAD |
| Japan | JP | Zengin | JPY |
| Australia | AU | AU BECS | AUD |
| Singapore | SG | GIRO | SGD |
| India | IN | NEFT | INR |
| Hong Kong | HK | CHATS | HKD |
| Switzerland | CH | SIC | CHF |
| Sweden | SE | Bankgirot | SEK |
| + 10 more | PL, DK, NZ, NO, RO, MX, IL, ID, HU | Local rails | Local |

### Idempotent Execution

Every payout run is safe to retry. The engine:
- Assigns a unique run ID to each execution
- Checks for existing `payment_order_id` before creating new orders
- Enforces `(liquidation_event_id, investor_id)` uniqueness at the database level
- Skips already-completed payouts with categorized skip reasons

### Categorized Exception Handling

Skipped payouts are categorized by reason for operational reporting:

```json
{
  "created": 45,
  "skipped": 7,
  "failed": 1,
  "skip_breakdown": {
    "existing_payment_order": 3,
    "missing_external_account": 2,
    "invalid_method": 1,
    "missing_country": 1
  }
}
```

### Exponential Backoff & Retry

Provider calls use production-grade retry logic:
- Exponential backoff: 1s → 2s → 4s → 8s → 16s (capped at 30s)
- Rate limit (429) handling with `Retry-After` header support
- Transient errors (502, 503, 504) are retried
- Permanent errors (400, 404) fail immediately

### Immutable Audit Trail

Every state change is logged as an append-only record:

```
AUDIT | run=abc123 payout=def456 action=rail_selected | {"country":"JP","rail":"zengin","currency":"JPY"}
AUDIT | run=abc123 payout=def456 action=payment_created | {"payment_order_id":"po_cross_border_a1b2c3"}
```

Use `GET /api/payouts/{id}/trace` to get the full audit trail for any payout.

---

## Quick Start

### Option 1: Docker

```bash
docker-compose up --build
```

### Option 2: Local

```bash
pip install -e ".[dev]"
python -m seed.seed_data       # Load sample data (60 investors, 30+ countries)
uvicorn app.main:app --reload  # Start API at http://localhost:8000
```

### Try It

```bash
# Trigger a payout run
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"liquidation_event_id": "LIQ-2024-001"}'

# Check run status
curl http://localhost:8000/api/runs

# List payouts by country
curl "http://localhost:8000/api/payouts?country=JP"

# Get full audit trace for a payout
curl http://localhost:8000/api/payouts/{payout_id}/trace

# Run it again — idempotent! (0 new payment orders)
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"liquidation_event_id": "LIQ-2024-001"}'
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest -v
```

Tests cover:
- **Rail selection**: All 30+ countries route correctly, edge cases (ABA routing, fallback)
- **Eligibility**: Categorized skip reasons for every failure mode
- **Orchestrator**: Full end-to-end run with routing verification
- **Idempotency**: Re-running the same event produces zero new payment orders

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Pydantic v2 |
| Database | SQLAlchemy 2.0, SQLite (async via aiosqlite) |
| Testing | pytest, pytest-asyncio, httpx |
| Containerization | Docker, docker-compose |
| Language | Python 3.10+ with type hints |

---

## Project Structure

```
payout-engine/
├── app/
│   ├── api/               # FastAPI route handlers
│   │   ├── runs.py        # POST/GET /api/runs — trigger and monitor runs
│   │   ├── payouts.py     # GET /api/payouts — query and trace payouts
│   │   └── health.py      # GET /health
│   ├── engine/
│   │   ├── orchestrator.py # Core payout execution engine
│   │   ├── eligibility.py  # Payment eligibility checks
│   │   └── retry.py        # Exponential backoff retry logic
│   ├── routing/
│   │   ├── rail_selector.py  # Multi-rail routing decision engine
│   │   └── country_rails.py  # 30+ country payment rail configuration
│   ├── providers/
│   │   ├── base.py          # Abstract PaymentProvider interface
│   │   └── mock_provider.py # Mock banking API (ACH/Wire/Cross-border)
│   ├── audit/
│   │   └── logger.py       # Immutable audit trail
│   └── models/
│       ├── payout.py        # SQLAlchemy models (PayoutRun, Payout, AuditLog)
│       └── enums.py         # Domain enumerations
├── seed/
│   └── seed_data.py         # Sample data: 60 investors across 30+ countries
├── tests/                   # pytest suite
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## Production Context

This demo implements the core patterns from a production system that:
- Processes **1,000+ investor payouts per liquidation event**
- Routes payments across **30+ countries** through **3 payment providers** (ACH, wire, cross-border)
- Reduced processing time from **~40 hours** (manual) to **~15 minutes** (automated)
- Achieved **94% payout completion on Day 1** of its first production run
- Maintains **zero duplicate payments** through idempotent design

The production system integrates with Modern Treasury, Dwolla, and Goldman Sachs TxB. This demo uses mock providers to demonstrate the architectural patterns without requiring real banking credentials.

---

## License

MIT
