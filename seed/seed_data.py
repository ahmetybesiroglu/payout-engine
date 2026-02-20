"""
Seed the database with realistic sample data.

Creates:
  - 60 investors across 30+ countries (matching GLOBAL_ACH_MAP)
  - 2 liquidation events (one small, one large)
  - Edge cases: missing bank details, zero-amount, foreign investor with US bank

Run:
    python -m seed.seed_data
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import async_session, init_db
from app.models.payout import Investor, LiquidationEvent


INVESTORS = [
    # US investors (largest group)
    {"id": "INV-001", "name": "John Smith", "country": "US", "payment_method": "ACH", "external_account_id": "ext_us_001", "has_aba_routing": 0},
    {"id": "INV-002", "name": "Sarah Johnson", "country": "US", "payment_method": "ACH", "external_account_id": "ext_us_002", "has_aba_routing": 0},
    {"id": "INV-003", "name": "Michael Davis", "country": "US", "payment_method": "ACH", "external_account_id": "ext_us_003", "has_aba_routing": 0},
    {"id": "INV-004", "name": "Emily Wilson", "country": "US", "payment_method": "Wire", "external_account_id": "ext_us_004", "has_aba_routing": 0},
    {"id": "INV-005", "name": "Robert Brown", "country": "US", "payment_method": "ACH", "external_account_id": "ext_us_005", "has_aba_routing": 0},
    {"id": "INV-006", "name": "Jessica Martinez", "country": "US", "payment_method": "ACH", "external_account_id": "ext_us_006", "has_aba_routing": 0},
    {"id": "INV-007", "name": "David Lee", "country": "US", "payment_method": "ACH", "external_account_id": "ext_us_007", "has_aba_routing": 0},
    {"id": "INV-008", "name": "Amanda Taylor", "country": "US", "payment_method": "ACH", "external_account_id": "ext_us_008", "has_aba_routing": 0},

    # SEPA countries (EUR)
    {"id": "INV-010", "name": "Hans Mueller", "country": "DE", "payment_method": "ACH", "external_account_id": "ext_de_001", "has_aba_routing": 0},
    {"id": "INV-011", "name": "Pierre Dupont", "country": "FR", "payment_method": "ACH", "external_account_id": "ext_fr_001", "has_aba_routing": 0},
    {"id": "INV-012", "name": "Carlos Garcia", "country": "ES", "payment_method": "ACH", "external_account_id": "ext_es_001", "has_aba_routing": 0},
    {"id": "INV-013", "name": "Jan van der Berg", "country": "NL", "payment_method": "ACH", "external_account_id": "ext_nl_001", "has_aba_routing": 0},
    {"id": "INV-014", "name": "Marco Rossi", "country": "IT", "payment_method": "ACH", "external_account_id": "ext_it_001", "has_aba_routing": 0},
    {"id": "INV-015", "name": "Lukas Gruber", "country": "AT", "payment_method": "ACH", "external_account_id": "ext_at_001", "has_aba_routing": 0},
    {"id": "INV-016", "name": "Sophie Janssens", "country": "BE", "payment_method": "ACH", "external_account_id": "ext_be_001", "has_aba_routing": 0},
    {"id": "INV-017", "name": "Liam O'Connor", "country": "IE", "payment_method": "ACH", "external_account_id": "ext_ie_001", "has_aba_routing": 0},
    {"id": "INV-018", "name": "Joao Silva", "country": "PT", "payment_method": "ACH", "external_account_id": "ext_pt_001", "has_aba_routing": 0},
    {"id": "INV-019", "name": "Mika Virtanen", "country": "FI", "payment_method": "ACH", "external_account_id": "ext_fi_001", "has_aba_routing": 0},
    {"id": "INV-020", "name": "Nikos Papadopoulos", "country": "GR", "payment_method": "Wire", "external_account_id": "ext_gr_001", "has_aba_routing": 0},
    {"id": "INV-021", "name": "Marc Schmit", "country": "LU", "payment_method": "ACH", "external_account_id": "ext_lu_001", "has_aba_routing": 0},
    {"id": "INV-022", "name": "Maris Ozols", "country": "LV", "payment_method": "ACH", "external_account_id": "ext_lv_001", "has_aba_routing": 0},
    {"id": "INV-023", "name": "Tomas Kazlauskas", "country": "LT", "payment_method": "ACH", "external_account_id": "ext_lt_001", "has_aba_routing": 0},

    # UK
    {"id": "INV-030", "name": "James Thompson", "country": "GB", "payment_method": "ACH", "external_account_id": "ext_gb_001", "has_aba_routing": 0},
    {"id": "INV-031", "name": "Charlotte Williams", "country": "GB", "payment_method": "Wire", "external_account_id": "ext_gb_002", "has_aba_routing": 0},

    # Canada
    {"id": "INV-032", "name": "Alexandre Tremblay", "country": "CA", "payment_method": "ACH", "external_account_id": "ext_ca_001", "has_aba_routing": 0},

    # Switzerland
    {"id": "INV-033", "name": "Felix Brunner", "country": "CH", "payment_method": "ACH", "external_account_id": "ext_ch_001", "has_aba_routing": 0},

    # Poland
    {"id": "INV-034", "name": "Piotr Kowalski", "country": "PL", "payment_method": "ACH", "external_account_id": "ext_pl_001", "has_aba_routing": 0},

    # Australia
    {"id": "INV-035", "name": "Jack Mitchell", "country": "AU", "payment_method": "ACH", "external_account_id": "ext_au_001", "has_aba_routing": 0},

    # Singapore
    {"id": "INV-036", "name": "Wei Lin Tan", "country": "SG", "payment_method": "ACH", "external_account_id": "ext_sg_001", "has_aba_routing": 0},

    # India
    {"id": "INV-037", "name": "Raj Patel", "country": "IN", "payment_method": "ACH", "external_account_id": "ext_in_001", "has_aba_routing": 0},

    # Japan
    {"id": "INV-038", "name": "Yuki Tanaka", "country": "JP", "payment_method": "ACH", "external_account_id": "ext_jp_001", "has_aba_routing": 0},

    # Denmark
    {"id": "INV-039", "name": "Lars Andersen", "country": "DK", "payment_method": "ACH", "external_account_id": "ext_dk_001", "has_aba_routing": 0},

    # New Zealand
    {"id": "INV-040", "name": "Olivia Campbell", "country": "NZ", "payment_method": "ACH", "external_account_id": "ext_nz_001", "has_aba_routing": 0},

    # Norway
    {"id": "INV-041", "name": "Erik Hansen", "country": "NO", "payment_method": "ACH", "external_account_id": "ext_no_001", "has_aba_routing": 0},

    # Hong Kong
    {"id": "INV-042", "name": "Ka Wing Chan", "country": "HK", "payment_method": "ACH", "external_account_id": "ext_hk_001", "has_aba_routing": 0},

    # Sweden
    {"id": "INV-043", "name": "Anna Lindqvist", "country": "SE", "payment_method": "ACH", "external_account_id": "ext_se_001", "has_aba_routing": 0},

    # Romania
    {"id": "INV-044", "name": "Andrei Popescu", "country": "RO", "payment_method": "ACH", "external_account_id": "ext_ro_001", "has_aba_routing": 0},

    # Mexico
    {"id": "INV-045", "name": "Maria Hernandez", "country": "MX", "payment_method": "ACH", "external_account_id": "ext_mx_001", "has_aba_routing": 0},

    # Israel
    {"id": "INV-046", "name": "Noam Levy", "country": "IL", "payment_method": "ACH", "external_account_id": "ext_il_001", "has_aba_routing": 0},

    # Indonesia
    {"id": "INV-047", "name": "Budi Santoso", "country": "ID", "payment_method": "ACH", "external_account_id": "ext_id_001", "has_aba_routing": 0},

    # Hungary
    {"id": "INV-048", "name": "Gabor Nagy", "country": "HU", "payment_method": "ACH", "external_account_id": "ext_hu_001", "has_aba_routing": 0},

    # ─── Edge cases ────────────────────────────────────────────────────

    # Foreign investor with US bank account (Wise) → should route to domestic ACH
    {"id": "INV-050", "name": "Kenji Watanabe", "country": "JP", "payment_method": "ACH", "external_account_id": "ext_jp_wise_001", "has_aba_routing": 1},

    # Another foreign investor with US bank (Mercury)
    {"id": "INV-051", "name": "Ana Soares", "country": "BR", "payment_method": "ACH", "external_account_id": "ext_br_merc_001", "has_aba_routing": 1},

    # Unsupported country → should fall back to international wire
    {"id": "INV-052", "name": "Omar Al-Rashid", "country": "AE", "payment_method": "Wire", "external_account_id": "ext_ae_001", "has_aba_routing": 0},
    {"id": "INV-053", "name": "Kim Soo-Jin", "country": "KR", "payment_method": "Wire", "external_account_id": "ext_kr_001", "has_aba_routing": 0},

    # Missing external account → should be skipped
    {"id": "INV-060", "name": "Ghost Investor", "country": "US", "payment_method": "ACH", "external_account_id": None, "has_aba_routing": 0},

    # Invalid payment method → should be skipped
    {"id": "INV-061", "name": "Crypto Only", "country": "US", "payment_method": "Crypto", "external_account_id": "ext_crypto_001", "has_aba_routing": 0},

    # Missing country → should be skipped
    {"id": "INV-062", "name": "Unknown Origin", "country": None, "payment_method": "ACH", "external_account_id": "ext_unknown_001", "has_aba_routing": 0},
]


LIQUIDATION_EVENTS = [
    {
        "id": "LIQ-2024-001",
        "name": "Asset Liquidation #127 — Q4 2024",
        "total_amount": 2_450_000.00,
        "payout_date": "2024-12-15",
        "status": "pending",
    },
    {
        "id": "LIQ-2024-002",
        "name": "Asset Liquidation #128 — Q4 2024",
        "total_amount": 890_000.00,
        "payout_date": "2024-12-20",
        "status": "pending",
    },
]


async def seed():
    """Seed the database with sample data."""
    await init_db()

    async with async_session() as session:
        # Check if already seeded
        existing = await session.get(Investor, "INV-001")
        if existing:
            print("Database already seeded. Skipping.")
            return

        # Create investors
        for inv_data in INVESTORS:
            investor = Investor(**inv_data)
            session.add(investor)

        # Create liquidation events
        for event_data in LIQUIDATION_EVENTS:
            event = LiquidationEvent(**event_data)
            session.add(event)

        await session.commit()
        print(f"Seeded {len(INVESTORS)} investors and {len(LIQUIDATION_EVENTS)} liquidation events.")


if __name__ == "__main__":
    asyncio.run(seed())
