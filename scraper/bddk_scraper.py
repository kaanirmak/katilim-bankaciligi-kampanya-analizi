"""
TEKNOFEST 2026 - BDDK Katılım Bankaları Listesi Scraper

BDDK'nın resmi web sitesinden katılım bankacılığı kuruluşlarının
listesini ve web sitesi bilgilerini çeker.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

from scraper.config import BDDK_KATILIM_BANKALARI_URL, DATA_PATHS, SCRAPER_CONFIG


def fetch_bddk_page(url: str = BDDK_KATILIM_BANKALARI_URL) -> Optional[str]:
    """BDDK katılım bankaları sayfasını indir.

    Args:
        url: BDDK kuruluş listesi URL'si.

    Returns:
        Sayfa HTML içeriği veya None (hata durumunda).
    """
    headers = {"User-Agent": SCRAPER_CONFIG["user_agent"]}
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=SCRAPER_CONFIG["timeout_seconds"],
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        logger.info(f"BDDK sayfası başarıyla indirildi: {url}")
        return response.text
    except requests.RequestException as e:
        logger.error(f"BDDK sayfası indirilemedi: {e}")
        return None


def parse_bank_list(html_content: str) -> list[dict]:
    """BDDK sayfasından katılım bankası listesini parse et.

    BDDK sayfası accordion (card) yapısında düzenlenmiştir.
    "Katılım Bankaları" başlıklı card'ı bulup altındaki
    banka isimlerini ve web sitesi linklerini çıkarır.

    Args:
        html_content: BDDK sayfasının HTML içeriği.

    Returns:
        Katılım bankası bilgilerini içeren sözlük listesi.
    """
    soup = BeautifulSoup(html_content, "lxml")
    banks = []

    # BDDK sayfası card/accordion yapısında
    # "Katılım Bankaları" başlıklı card-header'ı bul
    katilim_section = None
    for header in soup.find_all("div", class_="card-header"):
        header_text = header.get_text(strip=True)
        if "Katılım" in header_text:
            # Kardeş veya parent element'ten card-body'yi bul
            parent_card = header.find_parent("div", class_="card")
            if parent_card:
                katilim_section = parent_card.find("div", class_="card-body")
            if not katilim_section:
                # Bir sonraki kardeş element
                katilim_section = header.find_next_sibling("div")
            logger.info(f"Katılım Bankaları bölümü bulundu: {header_text}")
            break

    if not katilim_section:
        logger.warning("Katılım Bankaları bölümü bulunamadı. Tüm sayfa taranıyor...")
        katilim_section = soup

    # Bölümdeki li.row elemanlarından banka bilgilerini çıkar
    for li in katilim_section.find_all("li", class_="row"):
        # Web sitesi linkini bul
        link = li.find("a", href=True)
        if not link:
            continue
        href = link.get("href", "").strip()
        if not href.startswith("http"):
            continue

        # Banka adını çıkar: li içindeki child'lardan URL ve "Detay" dışındakileri al
        name_parts = []
        for child in li.children:
            text = child.get_text(strip=True) if hasattr(child, "get_text") else str(child).strip()
            if text and text != "Detay" and not text.startswith("http") and not text.startswith("("):
                name_parts.append(text)

        import re
        bank_name = " ".join(name_parts).strip()
        bank_name = re.sub(r"^\d+\.\s*", "", bank_name).strip()

        if not bank_name:
            bank_name = href  # Fallback: URL'yi kullan

        banks.append({
            "name": bank_name,
            "website": href,
            "source": "BDDK",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })

    logger.info(f"BDDK'dan {len(banks)} katılım bankası bulundu.")
    return banks


def save_bank_list(banks: list[dict], output_dir: str = DATA_PATHS["raw"]) -> str:
    """Banka listesini JSON dosyasına kaydet.

    Args:
        banks: Banka bilgileri listesi.
        output_dir: Çıktı dizini.

    Returns:
        Kaydedilen dosyanın yolu.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bddk_katilim_bankalari_{timestamp}.json"
    filepath = output_path / filename

    output_data = {
        "metadata": {
            "source": BDDK_KATILIM_BANKALARI_URL,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "total_banks": len(banks),
        },
        "banks": banks,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Banka listesi kaydedildi: {filepath}")
    return str(filepath)


def run_bddk_scraper() -> list[dict]:
    """BDDK scraper'ı çalıştır.

    Returns:
        Banka bilgileri listesi.
    """
    logger.info("BDDK Katılım Bankaları scraper başlatılıyor...")

    html_content = fetch_bddk_page()
    if html_content is None:
        logger.warning(
            "BDDK sayfası indirilemedi. Konfigürasyondaki statik liste kullanılacak."
        )
        # Statik listeyi config'den yükle
        from scraper.config import KATILIM_BANKALARI

        banks = [
            {
                "id": bank_id,
                "name": info["name"],
                "website": info["website"],
                "campaign_paths": info["campaign_paths"],
                "source": "static_config",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            for bank_id, info in KATILIM_BANKALARI.items()
        ]
    else:
        banks = parse_bank_list(html_content)

    if banks:
        save_bank_list(banks)
    else:
        logger.warning("Hiç banka bulunamadı!")

    return banks


if __name__ == "__main__":
    banks = run_bddk_scraper()
    for bank in banks:
        print(f"  - {bank['name']}: {bank.get('website', 'N/A')}")
