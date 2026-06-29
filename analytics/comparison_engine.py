"""
TEKNOFEST 2026 - Karşılaştırma Motoru

Yapılandırılmış kampanya verilerini çapraz sorgular,
karşılaştırır ve sıralar.
"""

from typing import Any, Optional

from loguru import logger


class ComparisonEngine:
    """Kampanya karşılaştırma motoru.

    Bankaların kampanyalarını çeşitli metriklere göre
    karşılaştırır ve sıralar.
    """

    def __init__(self):
        """ComparisonEngine'i başlat."""
        self.campaigns: list[dict] = []

    def load_campaigns(self, campaigns: list[dict]):
        """İşlenmiş kampanya verilerini yükle.

        Args:
            campaigns: Yapılandırılmış kampanya verileri listesi.
        """
        self.campaigns = campaigns
        logger.info(f"{len(campaigns)} kampanya karşılaştırma motoruna yüklendi.")

    def find_lowest_rate(
        self,
        category: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """En düşük kâr payı oranı sunan kampanyaları bul.

        Args:
            category: Filtreleme için kampanya kategorisi (opsiyonel).

        Returns:
            Kâr payı oranına göre sıralı kampanya listesi.
        """
        results = []

        for campaign in self.campaigns:
            if category and campaign.get("final_category") != category:
                continue

            summary = campaign.get("summary", {})
            rates = summary.get("rates", [])

            for rate in rates:
                results.append(
                    {
                        "bank_name": campaign.get("bank_name", "Bilinmeyen"),
                        "campaign_title": summary.get("campaign_title", campaign.get("title", "")),
                        "rate_value": rate["value"],
                        "rate_raw": rate.get("raw", ""),
                        "category": campaign.get("final_category_name", ""),
                    }
                )

        results.sort(key=lambda x: x["rate_value"])
        logger.info(f"En düşük kâr payı: {len(results)} sonuç bulundu.")
        return results

    def find_highest_reward(self) -> list[dict[str, Any]]:
        """En yüksek ödül/avantaj miktarını sağlayan kampanyaları bul.

        Returns:
            Ödül miktarına göre sıralı kampanya listesi.
        """
        results = []

        for campaign in self.campaigns:
            summary = campaign.get("summary", {})
            amounts = summary.get("amounts", [])

            # TRY cinsinden en yüksek tutarı bul
            try_amounts = [a for a in amounts if a.get("currency") == "TRY"]
            if try_amounts:
                max_amount = max(try_amounts, key=lambda a: a["value"])
                results.append(
                    {
                        "bank_name": campaign.get("bank_name", "Bilinmeyen"),
                        "campaign_title": summary.get("campaign_title", campaign.get("title", "")),
                        "amount_value": max_amount["value"],
                        "currency": "TRY",
                        "amount_raw": max_amount.get("raw", ""),
                        "category": campaign.get("final_category_name", ""),
                    }
                )

        results.sort(key=lambda x: x["amount_value"], reverse=True)
        logger.info(f"En yüksek ödül: {len(results)} sonuç bulundu.")
        return results

    def find_longest_maturity(self) -> list[dict[str, Any]]:
        """En uzun vade seçeneği sunan kampanyaları bul.

        Returns:
            Vade süresine göre sıralı kampanya listesi.
        """
        results = []

        for campaign in self.campaigns:
            summary = campaign.get("summary", {})
            durations = summary.get("durations", [])

            # Ay bazında en uzun vadeyi bul
            month_durations = [d for d in durations if d.get("unit") == "month"]
            if month_durations:
                max_duration = max(month_durations, key=lambda d: d["value"])
                results.append(
                    {
                        "bank_name": campaign.get("bank_name", "Bilinmeyen"),
                        "campaign_title": summary.get("campaign_title", campaign.get("title", "")),
                        "maturity_months": max_duration["value"],
                        "maturity_raw": max_duration.get("raw", ""),
                        "category": campaign.get("final_category_name", ""),
                    }
                )

        results.sort(key=lambda x: x["maturity_months"], reverse=True)
        logger.info(f"En uzun vade: {len(results)} sonuç bulundu.")
        return results

    def find_lowest_fee(self) -> list[dict[str, Any]]:
        """En düşük masraf/tahsis ücreti gerektiren kampanyaları bul.

        Masrafsız (0 TL) kampanyalar en üstte yer alır.

        Returns:
            Masraf tutarına göre sıralı kampanya listesi.
        """
        results = []

        for campaign in self.campaigns:
            summary = campaign.get("summary", {})

            # LLM'den gelen masraf bilgisi
            llm_data = campaign.get("llm_based", {})
            allocation_fee = None
            if llm_data:
                fee_info = llm_data.get("allocation_fee", {})
                if fee_info and fee_info.get("value") is not None:
                    allocation_fee = fee_info["value"]

            # Masrafsız kampanyalar
            text = campaign.get("full_text", "").lower()
            is_free = any(
                keyword in text
                for keyword in ["masrafsız", "ücretsiz", "0 tl tahsis", "tahsis ücreti yok"]
            )

            if allocation_fee is not None or is_free:
                results.append(
                    {
                        "bank_name": campaign.get("bank_name", "Bilinmeyen"),
                        "campaign_title": summary.get("campaign_title", campaign.get("title", "")),
                        "fee_value": 0 if is_free else allocation_fee,
                        "is_free": is_free,
                        "category": campaign.get("final_category_name", ""),
                    }
                )

        results.sort(key=lambda x: x["fee_value"])
        logger.info(f"En düşük masraf: {len(results)} sonuç bulundu.")
        return results

    def compare_banks(
        self,
        metric: str = "rate",
        category: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Bankaları belirli bir metriğe göre karşılaştır.

        Args:
            metric: Karşılaştırma metriği ("rate", "reward", "maturity", "fee").
            category: Filtreleme kategorisi.

        Returns:
            Sıralı karşılaştırma sonuçları.
        """
        method_map = {
            "rate": self.find_lowest_rate,
            "reward": self.find_highest_reward,
            "maturity": self.find_longest_maturity,
            "fee": self.find_lowest_fee,
        }

        if metric not in method_map:
            logger.error(f"Geçersiz metrik: {metric}. Geçerli metrikler: {list(method_map.keys())}")
            return []

        if metric == "rate":
            return method_map[metric](category=category)
        return method_map[metric]()

    def get_bank_summary(self) -> dict[str, Any]:
        """Tüm bankaların kampanya özetini oluştur.

        Returns:
            Banka bazında kampanya özet istatistikleri.
        """
        bank_stats = {}

        for campaign in self.campaigns:
            bank = campaign.get("bank_name", "Bilinmeyen")
            if bank not in bank_stats:
                bank_stats[bank] = {
                    "total_campaigns": 0,
                    "categories": {},
                    "min_rate": None,
                    "max_amount": None,
                    "max_maturity": None,
                }

            stats = bank_stats[bank]
            stats["total_campaigns"] += 1

            # Kategori dağılımı
            cat = campaign.get("final_category_name", "Bilinmeyen")
            stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

            # En düşük oran
            summary = campaign.get("summary", {})
            for rate in summary.get("rates", []):
                if stats["min_rate"] is None or rate["value"] < stats["min_rate"]:
                    stats["min_rate"] = rate["value"]

            # En yüksek tutar
            for amount in summary.get("amounts", []):
                if amount.get("currency") == "TRY":
                    if stats["max_amount"] is None or amount["value"] > stats["max_amount"]:
                        stats["max_amount"] = amount["value"]

            # En uzun vade
            for dur in summary.get("durations", []):
                if dur.get("unit") == "month":
                    if stats["max_maturity"] is None or dur["value"] > stats["max_maturity"]:
                        stats["max_maturity"] = dur["value"]

        return bank_stats
