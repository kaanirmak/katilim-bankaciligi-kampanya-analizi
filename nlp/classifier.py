"""
TEKNOFEST 2026 - Kampanya Sınıflandırıcı

Kampanya metinlerini belirlenen kategorilere otomatik sınıflandırır.
Hibrit yaklaşım: Anahtar kelime tabanlı + LLM tabanlı.
"""

from typing import Any, Optional

from loguru import logger

from nlp.llm_client import get_llm_client
from nlp.prompts.extraction import (
    CLASSIFICATION_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_CLASSIFIER,
)
from preprocessing.terminology_mapper import get_terminology_mapper

# Kategori tanımları
CAMPAIGN_CATEGORIES = {
    "ihtiyac_finansmani": {
        "name": "İhtiyaç Finansmanı Kampanyası",
        "description": "Bireylerin genel ihtiyaçları için sunulan finansman ürünleri.",
    },
    "konut_finansmani": {
        "name": "Konut Finansmanı Kampanyası",
        "description": "Konut alımı veya yenileme amaçlı finansman ürünleri.",
    },
    "tasit_finansmani": {
        "name": "Taşıt Finansmanı Kampanyası",
        "description": "Araç alımı amaçlı finansman ürünleri.",
    },
    "alisveris_puan_kart": {
        "name": "Alışveriş Puanı / Kart Kampanyası",
        "description": "Kart kullanımı ile ilgili puan, indirim ve avantaj kampanyaları.",
    },
    "yeni_musteri": {
        "name": "Yeni Müşteri Kampanyası",
        "description": "Yeni müşteri kazanımına yönelik kampanyalar.",
    },
    "yatirim_urunu": {
        "name": "Yatırım Ürünü Kampanyası",
        "description": "Yatırım ve birikim ürünlerine yönelik kampanyalar.",
    },
}


class CampaignClassifier:
    """Kampanya metin sınıflandırıcı.

    İki aşamalı sınıflandırma:
    1. Anahtar kelime tabanlı hızlı sınıflandırma
    2. LLM tabanlı derin sınıflandırma
    """

    def __init__(self, use_llm: bool = True):
        """CampaignClassifier'ı başlat.

        Args:
            use_llm: LLM tabanlı sınıflandırmayı aktifleştir.
        """
        self.use_llm = use_llm
        self.terminology_mapper = get_terminology_mapper()

        if use_llm:
            self.llm = get_llm_client()
        else:
            self.llm = None

    def classify_with_keywords(self, text: str) -> dict[str, Any]:
        """Anahtar kelime tabanlı sınıflandırma.

        Args:
            text: Kampanya metni.

        Returns:
            Sınıflandırma sonuçları.
        """
        categories = self.terminology_mapper.detect_category(text)

        if categories:
            primary = categories[0]
            return {
                "method": "keyword_based",
                "primary_category": primary["category_id"],
                "primary_category_name": primary["category_name"],
                "confidence": primary["confidence"],
                "all_categories": categories,
            }

        return {
            "method": "keyword_based",
            "primary_category": "unknown",
            "primary_category_name": "Bilinmeyen Kategori",
            "confidence": 0.0,
            "all_categories": [],
        }

    def classify_with_llm(self, text: str) -> Optional[dict[str, Any]]:
        """LLM tabanlı sınıflandırma.

        Args:
            text: Kampanya metni.

        Returns:
            LLM sınıflandırma sonuçları veya None.
        """
        if not self.llm or not self.llm.is_available:
            return None

        max_chars = 3000
        truncated = text[:max_chars] if len(text) > max_chars else text

        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(campaign_text=truncated)

        result = self.llm.generate_json(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_CLASSIFIER,
        )

        if result:
            result["method"] = "llm_based"

        return result

    def classify(self, text: str) -> dict[str, Any]:
        """Hibrit sınıflandırma (anahtar kelime + LLM).

        Args:
            text: Kampanya metni.

        Returns:
            Birleştirilmiş sınıflandırma sonuçları.
        """
        # Anahtar kelime tabanlı
        keyword_result = self.classify_with_keywords(text)

        # LLM tabanlı
        llm_result = None
        if self.use_llm:
            llm_result = self.classify_with_llm(text)

        # Sonuçları birleştir
        combined = {
            "keyword_classification": keyword_result,
            "llm_classification": llm_result,
        }

        # Final karar: LLM güveni yüksekse LLM, değilse keyword
        if llm_result and llm_result.get("confidence", 0) > 0.7:
            combined["final_category"] = llm_result.get("primary_category", keyword_result["primary_category"])
            combined["final_category_name"] = llm_result.get(
                "primary_category_name",
                keyword_result["primary_category_name"],
            )
            combined["final_confidence"] = llm_result.get("confidence", 0)
            combined["decision_source"] = "llm"
        else:
            combined["final_category"] = keyword_result["primary_category"]
            combined["final_category_name"] = keyword_result["primary_category_name"]
            combined["final_confidence"] = keyword_result["confidence"]
            combined["decision_source"] = "keyword"

        logger.info(
            f"Sınıflandırma: {combined['final_category_name']} "
            f"(güven: {combined['final_confidence']:.2f}, kaynak: {combined['decision_source']})"
        )

        return combined
