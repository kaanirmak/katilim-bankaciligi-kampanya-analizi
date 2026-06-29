"""
TEKNOFEST 2026 - Bilgi Çıkarımı Modülü (Entity Extractor)

Kampanya metinlerinden NER ve LLM tabanlı bilgi çıkarımı yapar.
Regex tabanlı kural motoru + LLM hibrit yaklaşım.
"""

import re
from typing import Any, Optional

from loguru import logger

from nlp.llm_client import get_llm_client
from nlp.prompts.extraction import (
    EXTRACTION_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_EXTRACTION,
)
from preprocessing.financial_normalizer import extract_all_financial_values
from preprocessing.terminology_mapper import get_terminology_mapper


class EntityExtractor:
    """Kampanya metinlerinden yapılandırılmış bilgi çıkarma sınıfı.

    Hibrit yaklaşım kullanır:
    1. Regex tabanlı kural motoru (hızlı, deterministik)
    2. LLM tabanlı çıkarım (derin, semantik)
    """

    def __init__(self, use_llm: bool = True):
        """EntityExtractor'ı başlat.

        Args:
            use_llm: LLM tabanlı çıkarımı aktifleştir.
        """
        self.use_llm = use_llm
        self.terminology_mapper = get_terminology_mapper()

        if use_llm:
            self.llm = get_llm_client()
        else:
            self.llm = None

    def extract_with_rules(self, text: str, bank_name: str = "") -> dict[str, Any]:
        """Regex tabanlı kural motoru ile bilgi çıkar.

        Args:
            text: Kampanya metni.
            bank_name: Banka adı.

        Returns:
            Çıkarılan bilgileri içeren sözlük.
        """
        # Finansal değerleri çıkar
        financials = extract_all_financial_values(text)

        # Terminoloji analizi
        terms = self.terminology_mapper.find_terms_in_text(text)
        categories = self.terminology_mapper.detect_category(text)

        # Hedef kitle tespiti
        target_audience = self._detect_target_audience(text)

        result = {
            "bank_name": bank_name,
            "extraction_method": "rule_based",
            "financial_values": financials,
            "terminology": terms,
            "detected_categories": categories,
            "target_audience": target_audience,
        }

        # En iyi kâr payı oranı
        if financials["rates"]:
            result["best_rate"] = min(financials["rates"], key=lambda r: r["value"])

        # En yüksek tutar
        try_amounts = [a for a in financials["amounts"] if a.get("currency") == "TRY"]
        if try_amounts:
            result["max_amount"] = max(try_amounts, key=lambda a: a["value"])

        # En uzun vade
        month_durations = [d for d in financials["durations"] if d.get("unit") == "month"]
        if month_durations:
            result["max_maturity"] = max(month_durations, key=lambda d: d["value"])

        # Tarihler
        if financials["dates"]:
            result["validity_dates"] = financials["dates"]

        return result

    def _detect_target_audience(self, text: str) -> list[str]:
        """Metinden hedef kitle bilgisini çıkar.

        Args:
            text: Kampanya metni.

        Returns:
            Tespit edilen hedef kitle segmentleri.
        """
        text_lower = text.lower()
        segments = []

        audience_keywords = {
            "yeni_musteri": ["yeni müşteri", "ilk kez", "hoş geldin", "yeni hesap"],
            "maas_musterisi": ["maaş müşterisi", "maaş", "bordro", "maaşını taşı"],
            "mevcut_musteri": ["mevcut müşteri", "sadık müşteri"],
            "emekli": ["emekli", "emeklilik"],
            "ogrenci": ["öğrenci", "üniversite"],
            "esnaf": ["esnaf", "küçük işletme", "KOBİ", "serbest meslek"],
            "kamu_calisani": ["kamu çalışanı", "memur", "devlet memuru"],
        }

        for segment, keywords in audience_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    segments.append(segment)
                    break

        return segments

    def extract_with_llm(
        self,
        text: str,
        bank_name: str = "",
    ) -> Optional[dict[str, Any]]:
        """LLM tabanlı derin bilgi çıkarımı.

        Args:
            text: Kampanya metni.
            bank_name: Banka adı.

        Returns:
            LLM'den çıkarılan yapılandırılmış bilgiler veya None.
        """
        if not self.llm or not self.llm.is_available:
            logger.warning("LLM kullanılabilir değil. LLM çıkarımı atlanıyor.")
            return None

        # Çok uzun metinleri kırp (token limiti)
        max_chars = 4000
        truncated_text = text[:max_chars] if len(text) > max_chars else text

        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            campaign_text=truncated_text,
            bank_name=bank_name,
        )

        result = self.llm.generate_json(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_EXTRACTION,
        )

        if result:
            result["extraction_method"] = "llm_based"

        return result

    def extract(
        self,
        text: str,
        bank_name: str = "",
    ) -> dict[str, Any]:
        """Hibrit bilgi çıkarımı (kural + LLM).

        Önce kural tabanlı çıkarım yapar, ardından LLM ile
        zenginleştirir ve birleştirir.

        Args:
            text: Kampanya metni.
            bank_name: Banka adı.

        Returns:
            Birleştirilmiş çıkarım sonuçları.
        """
        # Kural tabanlı çıkarım
        rule_result = self.extract_with_rules(text, bank_name)

        # LLM tabanlı çıkarım
        llm_result = None
        if self.use_llm:
            llm_result = self.extract_with_llm(text, bank_name)

        # Sonuçları birleştir
        combined = {
            "rule_based": rule_result,
            "llm_based": llm_result,
            "bank_name": bank_name,
        }

        # Birleştirilmiş özet
        combined["summary"] = self._merge_results(rule_result, llm_result)

        logger.info(
            f"Bilgi çıkarımı tamamlandı: {bank_name} | "
            f"Kural: {len(rule_result.get('financial_values', {}).get('rates', []))} oran | "
            f"LLM: {'başarılı' if llm_result else 'atlandı'}"
        )

        return combined

    def _merge_results(
        self,
        rule_result: dict,
        llm_result: Optional[dict],
    ) -> dict[str, Any]:
        """Kural ve LLM sonuçlarını birleştir.

        Kural tabanlı sonuçlar deterministik ve güvenilir,
        LLM sonuçları ek bağlam sağlar. Çakışmalarda
        kural tabanlı sonuçlar önceliklidir.

        Args:
            rule_result: Kural tabanlı çıkarım sonuçları.
            llm_result: LLM tabanlı çıkarım sonuçları.

        Returns:
            Birleştirilmiş özet sözlük.
        """
        merged = {
            "categories": rule_result.get("detected_categories", []),
            "target_audience": rule_result.get("target_audience", []),
            "rates": rule_result.get("financial_values", {}).get("rates", []),
            "amounts": rule_result.get("financial_values", {}).get("amounts", []),
            "durations": rule_result.get("financial_values", {}).get("durations", []),
            "dates": rule_result.get("financial_values", {}).get("dates", []),
        }

        if llm_result:
            # LLM'den gelen ek bilgiler
            if "campaign_title" in llm_result:
                merged["campaign_title"] = llm_result["campaign_title"]
            if "campaign_type" in llm_result:
                merged["campaign_type_llm"] = llm_result["campaign_type"]
            if "summary" in llm_result:
                merged["llm_summary"] = llm_result["summary"]
            if "conditions" in llm_result:
                merged["conditions"] = llm_result["conditions"]
            if "rewards" in llm_result:
                merged["rewards"] = llm_result["rewards"]

        return merged
