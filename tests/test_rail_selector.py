"""Tests for the multi-rail routing engine."""

from app.routing.rail_selector import select_rail


class TestUSPayments:
    def test_us_ach(self):
        result = select_rail("US", "ACH")
        assert result.payment_type == "ach"
        assert result.subtype == "CCD"
        assert result.currency == "USD"
        assert result.fx_indicator is None

    def test_us_wire_routes_to_ach(self):
        """US wire should still route to ACH (cheaper)."""
        result = select_rail("US", "Wire")
        assert result.payment_type == "ach"
        assert result.currency == "USD"


class TestSEPACountries:
    def test_germany_sepa(self):
        result = select_rail("DE", "ACH")
        assert result.payment_type == "cross_border"
        assert result.subtype == "sepa"
        assert result.currency == "EUR"
        assert result.fx_indicator == "fixed_to_variable"

    def test_france_sepa(self):
        result = select_rail("FR", "ACH")
        assert result.subtype == "sepa"
        assert result.currency == "EUR"

    def test_all_sepa_countries(self):
        sepa_countries = ["DE", "FR", "ES", "NL", "IT", "AT", "BE", "IE", "PT",
                          "FI", "GR", "LU", "CY", "MT", "SK", "LT", "SI", "EE", "LV"]
        for country in sepa_countries:
            result = select_rail(country)
            assert result.subtype == "sepa", f"Expected SEPA for {country}"
            assert result.currency == "EUR", f"Expected EUR for {country}"


class TestCountrySpecificRails:
    def test_uk_bacs(self):
        result = select_rail("GB")
        assert result.subtype == "bacs"
        assert result.currency == "GBP"

    def test_canada_eft_with_purpose(self):
        result = select_rail("CA")
        assert result.subtype == "eft"
        assert result.currency == "CAD"
        assert result.purpose == "250"

    def test_japan_zengin(self):
        result = select_rail("JP")
        assert result.subtype == "zengin"
        assert result.currency == "JPY"

    def test_australia_becs(self):
        result = select_rail("AU")
        assert result.subtype == "au_becs"
        assert result.currency == "AUD"

    def test_singapore_giro(self):
        result = select_rail("SG")
        assert result.subtype == "sg_giro"
        assert result.currency == "SGD"

    def test_india_neft(self):
        result = select_rail("IN")
        assert result.subtype == "neft"
        assert result.currency == "INR"

    def test_hong_kong_chats(self):
        result = select_rail("HK")
        assert result.subtype == "chats"
        assert result.currency == "HKD"

    def test_switzerland_sic(self):
        result = select_rail("CH")
        assert result.subtype == "sic"
        assert result.currency == "CHF"

    def test_mexico_ccen(self):
        result = select_rail("MX")
        assert result.subtype == "mx_ccen"
        assert result.currency == "MXN"


class TestForeignInvestorWithUSBank:
    def test_jp_investor_with_aba_routes_to_us_ach(self):
        """Japanese investor with Wise (US bank) should get domestic ACH."""
        result = select_rail("JP", "ACH", has_aba_routing=True)
        assert result.payment_type == "ach"
        assert result.subtype == "CCD"
        assert result.currency == "USD"
        assert "foreign investor" in result.label.lower()

    def test_us_investor_with_aba_stays_ach(self):
        """US investor with ABA is just normal domestic ACH."""
        result = select_rail("US", "ACH", has_aba_routing=True)
        assert result.payment_type == "ach"
        assert result.currency == "USD"


class TestFallback:
    def test_unsupported_country_falls_back_to_wire(self):
        result = select_rail("AE", "Wire")  # UAE not in GLOBAL_ACH_MAP
        assert result.payment_type == "wire"
        assert result.currency == "USD"

    def test_unknown_country(self):
        result = select_rail("ZZ")
        assert result.payment_type == "wire"

    def test_none_country(self):
        result = select_rail(None)
        assert result.payment_type == "wire"

    def test_empty_string_country(self):
        result = select_rail("")
        assert result.payment_type == "wire"
