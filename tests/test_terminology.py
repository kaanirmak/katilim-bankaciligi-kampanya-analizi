"""
TEKNOFEST 2026 - Terminoloji Eşleştirme Testleri
"""

import pytest

from preprocessing.terminology_mapper import TerminologyMapper


@pytest.fixture
def mapper():
    """TerminologyMapper test fixture."""
    return TerminologyMapper()


class TestTerminologyMapper:
    """Terminoloji eşleştirme testleri."""

    def test_direct_term_mapping(self, mapper):
        result = mapper.map_term("Faiz Oranı")
        assert result is not None
        assert result["participation_term"] == "Kâr Payı Oranı"

    def test_case_insensitive_mapping(self, mapper):
        result = mapper.map_term("faiz oranı")
        assert result is not None
        assert result["participation_term"] == "Kâr Payı Oranı"

    def test_alias_mapping(self, mapper):
        result = mapper.map_term("kredi")
        assert result is not None
        assert result["participation_term"] == "Finansman"

    def test_unknown_term(self, mapper):
        result = mapper.map_term("bilinmeyen terim xyz")
        assert result is None

    def test_find_terms_in_text(self, mapper):
        text = "Bu kampanyada faiz oranı %2,05 ile kredi kullandırılmaktadır."
        terms = mapper.find_terms_in_text(text)
        assert len(terms) > 0
        found_terms = [t["found_term"] for t in terms]
        assert "faiz oranı" in found_terms

    def test_detect_category_ihtiyac(self, mapper):
        text = "İhtiyaç finansmanı kampanyası ile bireysel müşterilerimize özel fırsatlar"
        categories = mapper.detect_category(text)
        assert len(categories) > 0
        assert categories[0]["category_id"] == "ihtiyac_finansmani"

    def test_detect_category_konut(self, mapper):
        text = "Konut finansmanı fırsatı! Hayalinizdeki eve kavuşun. Emlak ve gayrimenkul"
        categories = mapper.detect_category(text)
        assert len(categories) > 0
        assert categories[0]["category_id"] == "konut_finansmani"

    def test_detect_category_tasit(self, mapper):
        text = "Taşıt finansmanı kampanyası ile araç sahibi olun. Otomobil almak artık kolay"
        categories = mapper.detect_category(text)
        assert len(categories) > 0
        assert categories[0]["category_id"] == "tasit_finansmani"
