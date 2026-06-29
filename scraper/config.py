"""
TEKNOFEST 2026 - Scraper Konfigürasyonu
BDDK Katılım Bankası URL'leri ve scraping ayarları
"""

# BDDK Katılım Bankaları Listesi URL'si
BDDK_KATILIM_BANKALARI_URL = "https://www.bddk.org.tr/Kurulus/Liste/77"

# Bilinen Katılım Bankaları ve web siteleri
KATILIM_BANKALARI = {
    "albaraka_turk": {
        "name": "Albaraka Türk Katılım Bankası",
        "website": "https://www.albarakaturk.com.tr",
        "campaign_paths": ["/tr/kampanyalar"],
    },
    "kuveyt_turk": {
        "name": "Kuveyt Türk Katılım Bankası",
        "website": "https://www.kuveytturk.com.tr",
        "campaign_paths": ["/kampanyalar", "/kampanyalar/kendim-icin"],
    },
    "turkiye_finans": {
        "name": "Türkiye Finans Katılım Bankası",
        "website": "https://www.turkiyefinans.com.tr",
        "campaign_paths": ["/tr-tr/kampanyalar/Sayfalar/default.aspx", "/kampanyalar"],
    },
    "vakif_katilim": {
        "name": "Vakıf Katılım Bankası",
        "website": "https://www.vakifkatilim.com.tr",
        "campaign_paths": ["/tr/kendim-icin/kampanyalar/mevcut-kampanyalar", "/tr/bireysel/kampanyalar"],
    },
    "ziraat_katilim": {
        "name": "Ziraat Katılım Bankası",
        "website": "https://www.ziraatkatilim.com.tr",
        "campaign_paths": ["/bireysel/kampanyalar"],
    },
    "emlak_katilim": {
        "name": "Emlak Katılım Bankası",
        "website": "https://www.emlakkatilim.com.tr",
        "campaign_paths": ["/tr/bireysel/kampanyalar"],
    },
}

# Scraping Ayarları
SCRAPER_CONFIG = {
    "user_agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "request_delay_seconds": 2.0,       # İstekler arası bekleme süresi
    "max_retries": 3,                    # Maksimum yeniden deneme
    "timeout_seconds": 30,               # İstek zaman aşımı
    "concurrent_requests": 1,            # Eşzamanlı istek sayısı (nazik scraping)
    "respect_robots_txt": True,          # robots.txt'ye uyum
    "output_format": "json",             # Çıktı formatı
}

# Veri Kayıt Dizinleri
DATA_PATHS = {
    "raw": "data/raw",
    "processed": "data/processed",
    "database": "data/database",
}
