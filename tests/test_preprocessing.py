"""
TEKNOFEST 2026 - Finansal Normalizasyon Testleri
"""

import pytest

from preprocessing.financial_normalizer import (
    extract_all_financial_values,
    extract_amounts,
    extract_dates,
    extract_durations,
    extract_rates,
    normalize_number_format,
)


class TestNormalizeNumberFormat:
    """Türkçe sayı formatı normalizasyon testleri."""

    def test_turkish_decimal_comma(self):
        assert normalize_number_format("2,05") == "2.05"

    def test_turkish_thousands_with_decimal(self):
        assert normalize_number_format("1.000.000,50") == "1000000.50"

    def test_thousands_only(self):
        assert normalize_number_format("500.000") == "500000"

    def test_simple_number(self):
        assert normalize_number_format("500") == "500"

    def test_decimal_point(self):
        assert normalize_number_format("2.05") == "2.05"


class TestExtractRates:
    """Oran çıkarım testleri."""

    def test_percent_before(self):
        rates = extract_rates("%2,05 kâr payı oranı")
        assert len(rates) >= 1
        assert any(r["value"] == 2.05 for r in rates)

    def test_percent_after(self):
        rates = extract_rates("Kâr payı oranı 2.05%")
        assert len(rates) >= 1
        assert any(r["value"] == 2.05 for r in rates)

    def test_percent_with_space(self):
        rates = extract_rates("% 3,50 oranla")
        assert len(rates) >= 1
        assert any(r["value"] == 3.50 for r in rates)

    def test_yuzde_keyword(self):
        rates = extract_rates("yüzde 1,99 kâr payı")
        assert len(rates) >= 1
        assert any(r["value"] == 1.99 for r in rates)

    def test_no_rate(self):
        rates = extract_rates("Kampanya detayları için tıklayın")
        assert len(rates) == 0


class TestExtractAmounts:
    """Tutar çıkarım testleri."""

    def test_amount_with_tl(self):
        amounts = extract_amounts("500 TL hediye çeki")
        assert len(amounts) >= 1
        assert any(a["value"] == 500 and a["currency"] == "TRY" for a in amounts)

    def test_amount_with_lira_symbol(self):
        amounts = extract_amounts("₺1.000 nakit puan")
        assert len(amounts) >= 1
        assert any(a["value"] == 1000 and a["currency"] == "TRY" for a in amounts)

    def test_large_amount(self):
        amounts = extract_amounts("5.000.000 TL finansman")
        assert len(amounts) >= 1
        assert any(a["value"] == 5000000 and a["currency"] == "TRY" for a in amounts)


class TestExtractDurations:
    """Süre çıkarım testleri."""

    def test_months(self):
        durations = extract_durations("36 ay vade ile")
        assert len(durations) >= 1
        assert any(d["value"] == 36 and d["unit"] == "month" for d in durations)

    def test_installments(self):
        durations = extract_durations("12 taksit imkanı")
        assert len(durations) >= 1
        assert any(d["value"] == 12 and d["unit"] == "installment" for d in durations)

    def test_years(self):
        durations = extract_durations("5 yıllık finansman")
        assert len(durations) >= 1
        assert any(d["value"] == 5 and d["unit"] == "year" for d in durations)


class TestExtractDates:
    """Tarih çıkarım testleri."""

    def test_turkish_date(self):
        dates = extract_dates("31 Aralık 2026 tarihine kadar")
        assert len(dates) >= 1
        assert any(d["value"] == "2026-12-31" for d in dates)

    def test_numeric_date(self):
        dates = extract_dates("Geçerlilik: 01.06.2026")
        assert len(dates) >= 1
        assert any(d["value"] == "2026-06-01" for d in dates)


class TestExtractAllFinancials:
    """Tam finansal çıkarım testleri."""

    def test_complex_campaign_text(self):
        text = (
            "Kuveyt Türk'ten %1,89 kâr payı oranıyla 500.000 TL'ye kadar "
            "ihtiyaç finansmanı! 36 ay vade seçeneği. "
            "Kampanya 31 Aralık 2026 tarihine kadar geçerlidir."
        )
        result = extract_all_financial_values(text)

        assert len(result["rates"]) >= 1
        assert len(result["amounts"]) >= 1
        assert len(result["durations"]) >= 1
        assert len(result["dates"]) >= 1
