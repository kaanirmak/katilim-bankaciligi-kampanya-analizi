"""
TEKNOFEST 2026 - Finansal Değer Normalizasyon Modülü

Farklı yazım kurallarına sahip sayısal ifadeleri (oranlar, tutarlar,
para birimleri) standart formata dönüştürür.

Örnekler:
    - "%2,05", "% 2.05", "2.05%" → {"value": 2.05, "type": "rate"}
    - "500 TL", "500 Türk Lirası" → {"value": 500, "currency": "TRY"}
"""

import json
import re
from pathlib import Path
from typing import Any, Optional, Union

from loguru import logger

# Ontoloji dosyasından para birimi kalıplarını yükle
_ONTOLOGY_PATH = Path(__file__).parent.parent / "ontology" / "terminology.json"


def _load_currency_patterns() -> dict[str, list[str]]:
    """Ontoloji dosyasından para birimi kalıplarını yükle."""
    try:
        with open(_ONTOLOGY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("currency_patterns", {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Ontoloji dosyası yüklenemedi: {e}. Varsayılan kalıplar kullanılacak.")
        return {
            "TRY": ["TL", "Türk Lirası", "₺", "lira"],
            "USD": ["$", "Dolar", "ABD Doları", "USD"],
            "EUR": ["€", "Euro", "EUR"],
        }


CURRENCY_PATTERNS = _load_currency_patterns()


def normalize_number_format(text: str) -> str:
    """Türkçe sayı formatını standart formata dönüştür.

    Türkçe'de binlik ayırıcı "." ve ondalık ayırıcı "," kullanılır.
    Bu fonksiyon bunları standart "." ondalık formata dönüştürür.

    Args:
        text: Sayı içeren metin parçası.

    Returns:
        Standart ondalık formatlı sayı metni.

    Örnekler:
        "1.000.000,50" → "1000000.50"
        "2,05" → "2.05"
        "500.000" → "500000"
    """
    # Binlik ayırıcı + ondalık ayırıcı: 1.000.000,50
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", text):
        text = text.replace(".", "")  # Binlik noktaları kaldır
        text = text.replace(",", ".")  # Virgülü noktaya çevir
    # Sadece ondalık ayırıcı olarak virgül: 2,05
    elif re.match(r"^\d+,\d+$", text):
        text = text.replace(",", ".")
    # Binlik ayırıcı olarak nokta (ondalık yok): 500.000
    elif re.match(r"^\d{1,3}(\.\d{3})+$", text):
        text = text.replace(".", "")

    return text


def extract_rates(text: str) -> list[dict[str, Any]]:
    """Metinden oran/yüzde değerlerini çıkar ve normalize et.

    Desteklenen formatlar:
        %2,05  |  % 2.05  |  2.05%  |  2,05 %  |  yüzde 2,05

    Args:
        text: Oran içerebilen metin.

    Returns:
        Normalize edilmiş oran sözlükleri listesi.
    """
    rates = []

    patterns = [
        # %2,05 veya % 2,05
        r"%\s*(\d+[.,]?\d*)",
        # 2,05% veya 2.05 %
        r"(\d+[.,]?\d*)\s*%",
        # yüzde 2,05
        r"(?:yüzde|yuzde)\s+(\d+[.,]?\d*)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw_value = match.group(1)
            normalized = normalize_number_format(raw_value)
            try:
                value = float(normalized)
                rate_entry = {
                    "value": value,
                    "type": "rate",
                    "unit": "percent",
                    "raw": match.group(0).strip(),
                    "position": match.start(),
                }
                # Tekrar eden değerleri önle
                if not any(r["value"] == value and r["position"] == rate_entry["position"] for r in rates):
                    rates.append(rate_entry)
            except ValueError:
                logger.debug(f"Oran parse edilemedi: {raw_value}")

    return rates


def extract_amounts(text: str) -> list[dict[str, Any]]:
    """Metinden parasal tutarları çıkar ve normalize et.

    Desteklenen formatlar:
        500 TL  |  500 Türk Lirası  |  ₺500  |  1.000.000,50 TL

    Args:
        text: Tutar içerebilen metin.

    Returns:
        Normalize edilmiş tutar sözlükleri listesi.
    """
    amounts = []

    for currency_code, symbols in CURRENCY_PATTERNS.items():
        for symbol in symbols:
            escaped_symbol = re.escape(symbol)

            patterns = [
                # Tutar + birim: 500 TL, 1.000.000,50 TL, 500.000 TL'ye
                rf"(\d[\d.,]*)\s*{escaped_symbol}(?:\s|$|[.,;:!?)'\u2019])",
                # Birim + tutar: ₺500, $1.000
                rf"{escaped_symbol}\s*(\d[\d.,]*)",
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    raw_value = match.group(1)
                    normalized = normalize_number_format(raw_value)
                    try:
                        value = float(normalized)
                        amount_entry = {
                            "value": value,
                            "currency": currency_code,
                            "type": "amount",
                            "raw": match.group(0).strip(),
                            "position": match.start(),
                        }
                        if not any(
                            a["value"] == value
                            and a["currency"] == currency_code
                            and a["position"] == amount_entry["position"]
                            for a in amounts
                        ):
                            amounts.append(amount_entry)
                    except ValueError:
                        logger.debug(f"Tutar parse edilemedi: {raw_value}")

    return amounts


def extract_durations(text: str) -> list[dict[str, Any]]:
    """Metinden vade/süre bilgilerini çıkar.

    Desteklenen formatlar:
        36 ay  |  12 aylık  |  3 yıl  |  6 aylık vade

    Args:
        text: Süre bilgisi içerebilen metin.

    Returns:
        Normalize edilmiş süre sözlükleri listesi.
    """
    durations = []

    patterns = [
        # N ay / N aylık
        (r"(\d+)\s*(?:ay(?:lık)?)", "month"),
        # N yıl / N yıllık
        (r"(\d+)\s*(?:yıl(?:lık)?)", "year"),
        # N gün / N günlük
        (r"(\d+)\s*(?:gün(?:lük)?)", "day"),
        # N hafta / N haftalık
        (r"(\d+)\s*(?:hafta(?:lık)?)", "week"),
        # N taksit
        (r"(\d+)\s*taksit", "installment"),
    ]

    for pattern, unit in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = int(match.group(1))
            durations.append(
                {
                    "value": value,
                    "unit": unit,
                    "type": "duration",
                    "raw": match.group(0).strip(),
                    "position": match.start(),
                }
            )

    return durations


def extract_dates(text: str) -> list[dict[str, Any]]:
    """Metinden tarih bilgilerini çıkar.

    Args:
        text: Tarih içerebilen metin.

    Returns:
        Tarih sözlükleri listesi.
    """
    dates = []

    # Türkçe ay adları
    months_tr = {
        "ocak": "01", "şubat": "02", "mart": "03", "nisan": "04",
        "mayıs": "05", "haziran": "06", "temmuz": "07", "ağustos": "08",
        "eylül": "09", "ekim": "10", "kasım": "11", "aralık": "12",
    }

    # 31 Aralık 2026 formatı
    month_names = "|".join(months_tr.keys())
    pattern = rf"(\d{{1,2}})\s+({month_names})\s+(\d{{4}})"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        day = match.group(1).zfill(2)
        month = months_tr.get(match.group(2).lower(), "00")
        year = match.group(3)
        dates.append(
            {
                "value": f"{year}-{month}-{day}",
                "type": "date",
                "format": "ISO-8601",
                "raw": match.group(0).strip(),
                "position": match.start(),
            }
        )

    # DD.MM.YYYY veya DD/MM/YYYY formatı
    pattern = r"(\d{2})[./](\d{2})[./](\d{4})"
    for match in re.finditer(pattern, text):
        dates.append(
            {
                "value": f"{match.group(3)}-{match.group(2)}-{match.group(1)}",
                "type": "date",
                "format": "ISO-8601",
                "raw": match.group(0).strip(),
                "position": match.start(),
            }
        )

    return dates


def extract_all_financial_values(text: str) -> dict[str, list]:
    """Metinden tüm finansal değerleri çıkar ve normalize et.

    Args:
        text: Analiz edilecek metin.

    Returns:
        Tüm çıkarılan finansal değerleri içeren sözlük.
    """
    return {
        "rates": extract_rates(text),
        "amounts": extract_amounts(text),
        "durations": extract_durations(text),
        "dates": extract_dates(text),
    }


def normalize_campaign_financials(campaign: dict) -> dict:
    """Kampanya verisindeki tüm finansal değerleri normalize et.

    Args:
        campaign: Kampanya verisi sözlüğü.

    Returns:
        Finansal değerleri normalize edilmiş kampanya verisi.
    """
    normalized = campaign.copy()
    text = campaign.get("full_text", "")

    if text:
        normalized["extracted_financials"] = extract_all_financial_values(text)
        logger.debug(
            f"Finansal çıkarım: {len(normalized['extracted_financials']['rates'])} oran, "
            f"{len(normalized['extracted_financials']['amounts'])} tutar, "
            f"{len(normalized['extracted_financials']['durations'])} süre, "
            f"{len(normalized['extracted_financials']['dates'])} tarih"
        )

    return normalized
