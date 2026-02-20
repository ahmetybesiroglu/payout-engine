"""Tests for payment eligibility checks."""

from app.engine.eligibility import check_eligibility
from app.models.enums import SkipReason


class TestEligibility:
    def test_valid_ach_payout(self):
        result = check_eligibility("ACH", 1000.00, "ext_001", "US")
        assert result.eligible is True

    def test_valid_wire_payout(self):
        result = check_eligibility("Wire", 5000.00, "ext_002", "GB")
        assert result.eligible is True


class TestSkipReasons:
    def test_invalid_method(self):
        result = check_eligibility("Crypto", 1000.00, "ext_001", "US")
        assert not result.eligible
        assert result.skip_reason == SkipReason.INVALID_METHOD

    def test_none_method(self):
        result = check_eligibility(None, 1000.00, "ext_001", "US")
        assert not result.eligible
        assert result.skip_reason == SkipReason.INVALID_METHOD

    def test_zero_amount(self):
        result = check_eligibility("ACH", 0, "ext_001", "US")
        assert not result.eligible
        assert result.skip_reason == SkipReason.INVALID_AMOUNT

    def test_negative_amount(self):
        result = check_eligibility("ACH", -500.00, "ext_001", "US")
        assert not result.eligible
        assert result.skip_reason == SkipReason.INVALID_AMOUNT

    def test_none_amount(self):
        result = check_eligibility("ACH", None, "ext_001", "US")
        assert not result.eligible
        assert result.skip_reason == SkipReason.INVALID_AMOUNT

    def test_missing_external_account(self):
        result = check_eligibility("ACH", 1000.00, None, "US")
        assert not result.eligible
        assert result.skip_reason == SkipReason.MISSING_EXTERNAL_ACCOUNT

    def test_empty_external_account(self):
        result = check_eligibility("ACH", 1000.00, "", "US")
        assert not result.eligible
        assert result.skip_reason == SkipReason.MISSING_EXTERNAL_ACCOUNT

    def test_missing_country(self):
        result = check_eligibility("ACH", 1000.00, "ext_001", None)
        assert not result.eligible
        assert result.skip_reason == SkipReason.MISSING_COUNTRY

    def test_existing_payment_order(self):
        result = check_eligibility("ACH", 1000.00, "ext_001", "US", existing_payment_order_id="po_123")
        assert not result.eligible
        assert result.skip_reason == SkipReason.EXISTING_PAYMENT_ORDER


class TestPriorityOrder:
    def test_existing_po_checked_first(self):
        """Even with invalid method, existing PO should be the skip reason."""
        result = check_eligibility("Crypto", 1000.00, "ext_001", "US", existing_payment_order_id="po_123")
        assert result.skip_reason == SkipReason.EXISTING_PAYMENT_ORDER
