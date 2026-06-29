# TEKNOFEST 2026 - Yapay Zeka Dil Ajanları (2. Senaryo)

## 🏦 Katılım Bankacılığı Kampanya Analiz Sistemi

Katılım bankacılığına ait yapılandırılmamış kampanya metinlerini NLP ve LLM teknolojileri ile analiz eden, karşılaştıran ve son kullanıcılara dashboard ve chatbot arayüzleri üzerinden sunan **uçtan uca yapay zeka çözümü**.

> **⚠️ On-Premise:** Tüm bileşenler yerel sunucularda çalışır. Harici API servisleri (OpenAI, Anthropic vb.) kullanılmaz.

---

## 📁 Proje Yapısı

```
Teknofest/
├── scraper/                 # Katman 1: Veri Toplama (Web Scraping)
│   ├── bddk_scraper.py      # BDDK banka listesi çekme
│   ├── campaign_scraper.py  # Kampanya metinleri scraping
│   └── config.py            # URL listeleri ve ayarlar
│
├── preprocessing/           # Katman 2: Veri Ön İşleme
│   ├── text_cleaner.py      # HTML temizleme, normalizasyon
│   ├── financial_normalizer.py  # Oran, tutar, birim dönüşümleri
│   └── terminology_mapper.py    # Katılım bankacılığı terminolojisi
│
├── nlp/                     # Katman 3: NLP & LLM
│   ├── llm_client.py        # Yerel LLM entegrasyonu (Ollama)
│   ├── entity_extractor.py  # Bilgi çıkarımı (NER + LLM)
│   ├── classifier.py        # Kampanya sınıflandırma
│   └── prompts/             # LLM prompt şablonları
│
├── analytics/               # Katman 4: Karşılaştırma Motoru
│   └── comparison_engine.py # Çapraz sorgulama ve sıralama
│
├── app/                     # Katman 5: Arayüz
│   └── dashboard.py         # Streamlit dashboard + chatbot
│
├── ontology/                # Katılım Bankacılığı Ontolojisi
│   └── terminology.json     # Terim eşleştirme sözlüğü
│
├── data/                    # Veri Deposu
│   ├── raw/                 # Ham scraping çıktıları
│   ├── processed/           # İşlenmiş veriler
│   └── database/            # Veritabanı dosyaları
│
├── tests/                   # Test Dosyaları
├── requirements.txt         # Python bağımlılıkları
└── docker-compose.yml       # Docker konfigürasyonu
```

---

## 🚀 Kurulum

### Ön Koşullar
- Python 3.11+
- [Ollama](https://ollama.com/) (yerel LLM çalıştırma)
- Docker (opsiyonel)

### 1. Depoyu klonla
```bash
git clone https://github.com/<username>/Teknofest.git
cd Teknofest
```

### 2. Sanal ortam oluştur
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

### 3. Bağımlılıkları yükle
```bash
pip install -r requirements.txt
```

### 4. Ollama modelini indir
```bash
ollama pull llama3.1:8b
```

### 5. Dashboard'u başlat
```bash
streamlit run app/dashboard.py
```

---

## 🧪 Testler

```bash
pytest tests/ -v
```

---

## 🐳 Docker ile Çalıştırma

```bash
docker-compose up --build
```

---

## 📊 Kullanım

### Veri Toplama
```python
from scraper.bddk_scraper import run_bddk_scraper
from scraper.campaign_scraper import run_campaign_scraper

# BDDK'dan banka listesi çek
banks = run_bddk_scraper()

# Kampanya metinlerini topla
summary = run_campaign_scraper()
```

### Finansal Normalizasyon
```python
from preprocessing.financial_normalizer import extract_all_financial_values

text = "%1,89 kâr payı ile 500.000 TL finansman, 36 ay vade"
result = extract_all_financial_values(text)
# {'rates': [{'value': 1.89, ...}], 'amounts': [{'value': 500000, ...}], ...}
```

### Kampanya Karşılaştırma
```python
from analytics.comparison_engine import ComparisonEngine

engine = ComparisonEngine()
engine.load_campaigns(processed_campaigns)
lowest_rates = engine.find_lowest_rate()
```

---

## 📜 Lisans

Apache License 2.0

---

## 🏷️ Etiket

`BilisimVadisi2026`
