"""
TEKNOFEST 2026 - Uçtan Uca Kampanya İşleme Pipeline'ı

Bu betik, ham scraping çıktılarını yükler, temizler, normalleştirir,
yerel LLM kullanarak ek veri çıkarımı ve sınıflandırma yapar
ve sonuçları işlenmiş olarak kaydeder.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
from loguru import logger
from tqdm import tqdm

def safe_tqdm(iterable, **kwargs):
    if "streamlit" in sys.modules or not sys.stderr.isatty():
        kwargs["disable"] = True
    return tqdm(iterable, **kwargs)

from preprocessing.text_cleaner import clean_campaign_data
from preprocessing.financial_normalizer import normalize_campaign_financials
from preprocessing.terminology_mapper import get_terminology_mapper
from nlp.entity_extractor import EntityExtractor
from nlp.classifier import CampaignClassifier

# Dizin tanımları
RAW_DIR = Path("data/raw/campaigns")
PROCESSED_DIR = Path("data/processed")


def run_pipeline(limit: int = 0, force_no_llm: bool = False):
    """Kampanya işleme hattını çalıştır.

    Args:
        limit: Test amaçlı işlenecek maksimum kampanya sayısı. 0 ise hepsi.
        force_no_llm: True ise LLM analizlerini atlar (hızlı kural tabanlı mod).
    """
    logger.info("Uçtan Uca Kampanya İşleme Pipeline'ı başlatılıyor...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Ham kampanya dosyalarını bul
    raw_files = list(RAW_DIR.glob("*.json"))
    if not raw_files:
        logger.error(f"'{RAW_DIR}' dizininde ham kampanya dosyası bulunamadı!")
        return

    logger.info(f"Bulunan dosya sayısı: {len(raw_files)}")

    # 2. Modülleri başlat
    mapper = get_terminology_mapper()
    
    # LLM kullanılabilir mi kontrol et
    use_llm = False
    if not force_no_llm:
        from nlp.llm_client import get_llm_client
        llm_client = get_llm_client()
        use_llm = llm_client.is_available
        
        if use_llm:
            logger.info(f"Yerel LLM aktif: {llm_client.model}")
        else:
            logger.warning("Yerel LLM sunucusuna bağlanılamadı. Sadece kural tabanlı çıkarım yapılacak.")
    else:
        logger.info("Kural tabanlı (Hızlı) mod aktif. LLM analizi atlanıyor.")

    extractor = EntityExtractor(use_llm=use_llm)
    classifier = CampaignClassifier(use_llm=use_llm)

    all_processed_campaigns = []

    # 3. Dosyaları yükle ve işle
    for raw_file in raw_files:
        logger.info(f"İşleniyor: {raw_file.name}")
        with open(raw_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        campaigns = data.get("campaigns", [])
        bank_id = data.get("metadata", {}).get("bank_id", "bilinmeyen")

        # Limit uygula
        if limit > 0:
            campaigns = campaigns[:limit]
            logger.info(f"Limit uygulandı: sadece {limit} kampanya işlenecek.")

        processed_list = []
        for campaign in tqdm(campaigns, desc=f"{bank_id} Kampanyaları"):
            try:
                # A. Metin Temizleme
                cleaned = clean_campaign_data(campaign)

                # B. Finansal Değer Normalizasyonu
                normalized = normalize_campaign_financials(cleaned)

                # C. Terminoloji Zenginleştirme
                enriched = mapper.enrich_campaign(normalized)

                # D. Hibrit Bilgi Çıkarımı
                extraction = extractor.extract(enriched["full_text"], enriched.get("bank_name", ""))
                enriched["summary"] = extraction.get("summary", {})
                enriched["llm_based"] = extraction.get("llm_based")
                enriched["rule_based"] = extraction.get("rule_based")

                # E. Kampanya Sınıflandırma
                class_info = classifier.classify(enriched["full_text"])
                enriched["final_category"] = class_info.get("final_category")
                enriched["final_category_name"] = class_info.get("final_category_name")
                enriched["final_confidence"] = class_info.get("final_confidence")
                enriched["classification_details"] = class_info

                processed_list.append(enriched)
            except Exception as e:
                logger.error(f"Kampanya işlenirken hata oluştu ({campaign.get('title', 'N/A')}): {e}")

        # Banka bazında kaydet
        bank_output_file = PROCESSED_DIR / f"processed_campaigns_{bank_id}.json"
        output_data = {
            "metadata": {
                "bank_id": bank_id,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "total_processed": len(processed_list),
                "llm_used": use_llm,
            },
            "campaigns": processed_list,
        }
        with open(bank_output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Banka kampanyaları kaydedildi: {bank_output_file}")
        
        all_processed_campaigns.extend(processed_list)

    # Genel konsolide dosyayı kaydet
    consolidated_file = PROCESSED_DIR / "processed_campaigns.json"
    consolidated_data = {
        "metadata": {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "total_processed": len(all_processed_campaigns),
            "llm_used": use_llm,
        },
        "campaigns": all_processed_campaigns,
    }
    with open(consolidated_file, "w", encoding="utf-8") as f:
        json.dump(consolidated_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Pipeline tamamlandı. Toplam {len(all_processed_campaigns)} kampanya işlendi.")
    logger.info(f"Konsolide sonuçlar kaydedildi: {consolidated_file}")


if __name__ == "__main__":
    import sys
    # İlk parametre olarak limit verilebilir
    limit = 0
    force_no_llm = False

    if len(sys.argv) > 1:
        if "--no-llm" in sys.argv:
            force_no_llm = True
            sys.argv.remove("--no-llm")

    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass

    run_pipeline(limit=limit, force_no_llm=force_no_llm)
