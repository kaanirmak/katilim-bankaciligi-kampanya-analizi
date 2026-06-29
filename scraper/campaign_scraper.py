"""
TEKNOFEST 2026 - Kampanya Metinleri Scraper

Katılım bankalarının web sitelerinden kampanya metinlerini,
ürün detaylarını ve kart avantaj açıklamalarını toplar.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from loguru import logger

from scraper.config import DATA_PATHS, KATILIM_BANKALARI, SCRAPER_CONFIG


def fetch_page(url: str) -> Optional[str]:
    """Bir web sayfasını indir.

    Args:
        url: İndirilecek sayfanın URL'si.

    Returns:
        HTML içeriği veya None (hata durumunda).
    """
    headers = {"User-Agent": SCRAPER_CONFIG["user_agent"]}

    for attempt in range(1, SCRAPER_CONFIG["max_retries"] + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=SCRAPER_CONFIG["timeout_seconds"],
            )
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except requests.RequestException as e:
            logger.warning(f"Deneme {attempt}/{SCRAPER_CONFIG['max_retries']} başarısız: {url} - {e}")
            if attempt < SCRAPER_CONFIG["max_retries"]:
                time.sleep(SCRAPER_CONFIG["request_delay_seconds"] * attempt)

    logger.error(f"Sayfa indirilemedi (tüm denemeler tükendi): {url}")
    return None


def extract_campaign_links(html_content: str, base_url: str) -> list[dict]:
    """Kampanya listesi sayfasından kampanya bağlantılarını çıkar.

    Args:
        html_content: Kampanya listesi sayfasının HTML içeriği.
        base_url: Bağlantıları çözmek için temel URL.

    Returns:
        Kampanya bağlantıları ve başlıklarını içeren sözlük listesi.
    """
    soup = BeautifulSoup(html_content, "lxml")
    campaigns = []

    # Genel kampanya kart/liste yapılarını tara
    selectors = [
        "div.campaign-item",
        "div.kampanya-item",
        "article.campaign",
        "div.card",
        "li.campaign-list-item",
        "div.kampanya-card",
    ]

    campaign_elements = []
    for selector in selectors:
        found = soup.select(selector)
        if found:
            campaign_elements = found
            break

    # Eğer özel selector bulunamazsa, tüm linklerden kampanya olanları filtrele
    if not campaign_elements:
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if any(
                keyword in href.lower() or keyword in text.lower()
                for keyword in ["kampanya", "firsat", "avantaj", "campaign"]
            ):
                full_url = urljoin(base_url, href)
                if full_url not in [c["url"] for c in campaigns]:
                    campaigns.append(
                        {
                            "title": text or "Başlıksız Kampanya",
                            "url": full_url,
                        }
                    )
    else:
        for element in campaign_elements:
            link = element.find("a", href=True)
            title_el = element.find(["h2", "h3", "h4", "span", "p"])
            title = (
                title_el.get_text(strip=True) if title_el else "Başlıksız Kampanya"
            )
            url = urljoin(base_url, link.get("href", "")) if link else ""

            if url:
                campaigns.append({"title": title, "url": url})

    logger.info(f"{base_url} adresinden {len(campaigns)} kampanya bağlantısı bulundu.")
    return campaigns


def extract_campaign_content(html_content: str, url: str) -> dict:
    """Kampanya detay sayfasından metin içeriğini çıkar.

    Args:
        html_content: Kampanya detay sayfasının HTML içeriği.
        url: Kampanya sayfasının URL'si.

    Returns:
        Kampanya metin içeriği ve meta bilgilerini içeren sözlük.
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Gereksiz elementleri kaldır
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Ana içerik alanını bul
    content_selectors = [
        "article",
        "div.content",
        "div.campaign-detail",
        "div.kampanya-detay",
        "main",
        "div.page-content",
    ]

    main_content = None
    for selector in content_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break

    if not main_content:
        main_content = soup.find("body") or soup

    # Başlık çıkar
    title = ""
    title_el = soup.find("h1") or soup.find("title")
    if title_el:
        title = title_el.get_text(strip=True)

    # Tüm metin paragraflarını çıkar
    paragraphs = []
    for p in main_content.find_all(["p", "li", "td", "span", "div"]):
        text = p.get_text(strip=True)
        if text and len(text) > 10:  # Çok kısa metinleri atla
            paragraphs.append(text)

    # Tabloları ayrıca çıkar (finansal veriler genellikle tablolarda)
    tables = []
    for table in main_content.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)

    # Meta açıklama
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")

    full_text = "\n".join(paragraphs)

    return {
        "title": title,
        "url": url,
        "full_text": full_text,
        "paragraphs": paragraphs,
        "tables": tables,
        "meta_description": meta_desc,
        "text_length": len(full_text),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def scrape_bank_campaigns(
    bank_id: str,
    bank_info: dict,
) -> list[dict]:
    """Bir bankanın tüm kampanya metinlerini topla.

    Args:
        bank_id: Banka tanımlayıcısı.
        bank_info: Banka bilgileri sözlüğü (config'den).

    Returns:
        Kampanya içeriklerini içeren sözlük listesi.
    """
    logger.info(f"Kampanya scraping başlıyor: {bank_info['name']}")
    all_campaigns = []

    for path in bank_info["campaign_paths"]:
        campaign_list_url = bank_info["website"] + path
        logger.info(f"  Kampanya listesi: {campaign_list_url}")

        html = fetch_page(campaign_list_url)
        if not html:
            continue

        campaign_links = extract_campaign_links(html, campaign_list_url)

        for link_info in campaign_links:
            time.sleep(SCRAPER_CONFIG["request_delay_seconds"])

            campaign_html = fetch_page(link_info["url"])
            if not campaign_html:
                continue

            content = extract_campaign_content(campaign_html, link_info["url"])
            content["bank_id"] = bank_id
            content["bank_name"] = bank_info["name"]
            content["listing_title"] = link_info["title"]

            all_campaigns.append(content)
            logger.info(
                f"    ✓ Kampanya toplandı: {content['title'][:60]}... "
                f"({content['text_length']} karakter)"
            )

    logger.info(
        f"{bank_info['name']}: Toplam {len(all_campaigns)} kampanya toplandı."
    )
    return all_campaigns


def save_campaigns(
    campaigns: list[dict],
    bank_id: str,
    output_dir: str = DATA_PATHS["raw"],
) -> str:
    """Kampanya verilerini JSON dosyasına kaydet.

    Args:
        campaigns: Kampanya içerikleri listesi.
        bank_id: Banka tanımlayıcısı.
        output_dir: Çıktı dizini.

    Returns:
        Kaydedilen dosyanın yolu.
    """
    output_path = Path(output_dir) / "campaigns"
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"campaigns_{bank_id}_{timestamp}.json"
    filepath = output_path / filename

    output_data = {
        "metadata": {
            "bank_id": bank_id,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "total_campaigns": len(campaigns),
            "total_text_chars": sum(c["text_length"] for c in campaigns),
        },
        "campaigns": campaigns,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Kampanyalar kaydedildi: {filepath}")
    return str(filepath)


def run_campaign_scraper(bank_ids: Optional[list[str]] = None) -> dict:
    """Tüm bankaların veya belirtilen bankaların kampanyalarını topla.

    Args:
        bank_ids: Scrape edilecek banka ID listesi. None ise tüm bankalar.

    Returns:
        Banka bazında toplanan kampanya sayılarını içeren özet sözlük.
    """
    logger.info("Kampanya scraper başlatılıyor...")

    target_banks = bank_ids or list(KATILIM_BANKALARI.keys())
    summary = {}

    for bank_id in target_banks:
        if bank_id not in KATILIM_BANKALARI:
            logger.warning(f"Bilinmeyen banka ID: {bank_id}")
            continue

        bank_info = KATILIM_BANKALARI[bank_id]
        campaigns = scrape_bank_campaigns(bank_id, bank_info)

        if campaigns:
            save_campaigns(campaigns, bank_id)

        summary[bank_id] = {
            "name": bank_info["name"],
            "campaigns_collected": len(campaigns),
        }

    logger.info(f"Kampanya scraper tamamlandı. Özet: {json.dumps(summary, ensure_ascii=False)}")
    return summary


if __name__ == "__main__":
    summary = run_campaign_scraper()
    print("\n=== Kampanya Toplama Özeti ===")
    for bank_id, info in summary.items():
        print(f"  {info['name']}: {info['campaigns_collected']} kampanya")
