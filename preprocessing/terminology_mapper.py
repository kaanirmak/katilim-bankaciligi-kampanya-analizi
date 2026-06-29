"""
TEKNOFEST 2026 - Terminoloji Eşleştirme Modülü

Geleneksel bankacılık terimlerini katılım bankacılığı
karşılıklarıyla eşleştirir ve metinlerdeki terminoloji
tutarsızlıklarını tespit eder.
"""

import json
from pathlib import Path
from typing import Any, Optional

from loguru import logger

_ONTOLOGY_PATH = Path(__file__).parent.parent / "ontology" / "terminology.json"


def _turkish_lower(text: str) -> str:
    """Türkçe'ye özel küçük harf dönüşümü.

    Python'ın str.lower() metodu Türkçe İ→i ve I→ı dönüşümlerini
    doğru yapamaz. Bu fonksiyon bu sorunu çözer.
    """
    text = text.replace("İ", "i").replace("I", "ı")
    return text.lower()


class TerminologyMapper:
    """Katılım bankacılığı terminoloji eşleştirme sınıfı.

    Geleneksel bankacılık kavramlarını faizsiz finans karşılıklarıyla
    eşleştirir ve metinlerde doğru terminoloji kullanımını doğrular.
    """

    def __init__(self, ontology_path: Optional[str] = None):
        """TerminologyMapper'ı başlat.

        Args:
            ontology_path: Ontoloji JSON dosyasının yolu.
                           None ise varsayılan dosya kullanılır.
        """
        self.ontology_path = Path(ontology_path) if ontology_path else _ONTOLOGY_PATH
        self._load_ontology()

    def _load_ontology(self):
        """Ontoloji dosyasını yükle."""
        try:
            with open(self.ontology_path, "r", encoding="utf-8") as f:
                self.ontology = json.load(f)

            self.terminology = self.ontology.get("terminology_mapping", [])
            self.categories = self.ontology.get("campaign_categories", [])

            # Hızlı arama için indeksler oluştur
            self._build_lookup_indexes()
            logger.info(
                f"Ontoloji yüklendi: {len(self.terminology)} terim, "
                f"{len(self.categories)} kategori"
            )
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Ontoloji dosyası yüklenemedi: {e}")
            self.ontology = {}
            self.terminology = []
            self.categories = []
            self._conventional_to_participation = {}
            self._alias_to_participation = {}
            self._category_keywords = {}

    def _build_lookup_indexes(self):
        """Hızlı arama indeksleri oluştur."""
        # Geleneksel terim → katılım terimi eşleşmesi
        self._conventional_to_participation = {}
        # Alias → katılım terimi eşleşmesi
        self._alias_to_participation = {}

        for entry in self.terminology:
            conventional = _turkish_lower(entry["conventional_term"])
            participation = entry["participation_term"]

            self._conventional_to_participation[conventional] = entry

            for alias in entry.get("aliases", []):
                self._alias_to_participation[_turkish_lower(alias)] = entry

        # Kategori → anahtar kelimeler
        self._category_keywords = {}
        for cat in self.categories:
            self._category_keywords[cat["id"]] = {
                "name": cat["name"],
                "keywords": [_turkish_lower(k) for k in cat.get("keywords", [])],
                "description": cat.get("description", ""),
            }

    def map_term(self, term: str) -> Optional[dict[str, Any]]:
        """Bir terimi katılım bankacılığı karşılığıyla eşleştir.

        Args:
            term: Eşleştirilecek bankacılık terimi.

        Returns:
            Eşleşme bilgileri sözlüğü veya None.
        """
        term_lower = _turkish_lower(term).strip()

        # Doğrudan geleneksel terim eşleşmesi
        if term_lower in self._conventional_to_participation:
            entry = self._conventional_to_participation[term_lower]
            return {
                "original_term": term,
                "conventional_term": entry["conventional_term"],
                "participation_term": entry["participation_term"],
                "description": entry["technical_description"],
                "category": entry.get("category", ""),
                "match_type": "direct",
            }

        # Alias eşleşmesi
        if term_lower in self._alias_to_participation:
            entry = self._alias_to_participation[term_lower]
            return {
                "original_term": term,
                "conventional_term": entry["conventional_term"],
                "participation_term": entry["participation_term"],
                "description": entry["technical_description"],
                "category": entry.get("category", ""),
                "match_type": "alias",
            }

        return None

    def find_terms_in_text(self, text: str) -> list[dict[str, Any]]:
        """Metinde geçen bankacılık terimlerini bul ve eşleştir.

        Args:
            text: Analiz edilecek metin.

        Returns:
            Bulunan terimlerin eşleştirme bilgileri listesi.
        """
        text_lower = _turkish_lower(text)
        found_terms = []

        # Geleneksel terimleri ara
        for conventional, entry in self._conventional_to_participation.items():
            if conventional in text_lower:
                found_terms.append(
                    {
                        "found_term": conventional,
                        "participation_term": entry["participation_term"],
                        "description": entry["technical_description"],
                        "category": entry.get("category", ""),
                        "match_type": "conventional_term_in_text",
                    }
                )

        # Katılım terimlerini ara
        for entry in self.terminology:
            participation_lower = _turkish_lower(entry["participation_term"])
            if participation_lower in text_lower:
                found_terms.append(
                    {
                        "found_term": entry["participation_term"],
                        "participation_term": entry["participation_term"],
                        "description": entry["technical_description"],
                        "category": entry.get("category", ""),
                        "match_type": "participation_term_in_text",
                    }
                )

        return found_terms

    def detect_category(self, text: str) -> list[dict[str, Any]]:
        """Metnin kampanya kategorisini tespit et.

        Args:
            text: Analiz edilecek kampanya metni.

        Returns:
            Eşleşen kategoriler ve güven skorları.
        """
        text_lower = _turkish_lower(text)
        category_scores = []

        for cat_id, cat_info in self._category_keywords.items():
            score = 0
            matched_keywords = []
            for keyword in cat_info["keywords"]:
                if keyword in text_lower:
                    score += 1
                    matched_keywords.append(keyword)

            if score > 0:
                category_scores.append(
                    {
                        "category_id": cat_id,
                        "category_name": cat_info["name"],
                        "description": cat_info["description"],
                        "score": score,
                        "total_keywords": len(cat_info["keywords"]),
                        "confidence": round(score / len(cat_info["keywords"]), 2),
                        "matched_keywords": matched_keywords,
                    }
                )

        # Skora göre sırala (yüksekten düşüğe)
        category_scores.sort(key=lambda x: x["score"], reverse=True)
        return category_scores

    def enrich_campaign(self, campaign: dict) -> dict:
        """Kampanya verisini terminoloji bilgileriyle zenginleştir.

        Args:
            campaign: Kampanya verisi sözlüğü.

        Returns:
            Terminoloji bilgileriyle zenginleştirilmiş kampanya.
        """
        enriched = campaign.copy()
        text = campaign.get("full_text", "")

        if text:
            enriched["terminology_analysis"] = {
                "found_terms": self.find_terms_in_text(text),
                "detected_categories": self.detect_category(text),
            }

        return enriched


# Modül seviyesinde singleton instance
_mapper_instance: Optional[TerminologyMapper] = None


def get_terminology_mapper() -> TerminologyMapper:
    """Global TerminologyMapper instance'ını döndür."""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = TerminologyMapper()
    return _mapper_instance
