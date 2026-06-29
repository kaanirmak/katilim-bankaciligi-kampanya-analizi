# TEKNOFEST 2026 - Yapay Zeka Dil Ajanları Yarışması (2. Senaryo)
## Katılım Bankacılığı Kampanya Analiz ve Karşılaştırma Ajanı Kurulum Kılavuzu

Bu kılavuz, projenin on-premise (yerel) ortamda kurulması, yapılandırılması ve çalıştırılması için gerekli tüm adımları içerir. Proje, dış API'lere bağımlılığı olmayan (100% On-Premise) ve açık kaynak kodlu bileşenlerden oluşan bir mimariye sahiptir.

---

## 📋 Gereksinimler

- **İşletim Sistemi**: macOS (Apple Silicon tavsiye edilir), Linux veya Windows (WSL2 ile)
- **Python**: Python 3.9 veya üzeri (Python 3.11 tavsiye edilir)
- **Docker & Docker Compose**: Konteynerize kurulum için
- **Ollama**: Yerel LLM modeli çalıştırılması için (en az 8GB VRAM/RAM tavsiye edilir)

---

## 🛠️ Yerel (Lokal) Kurulum Adımları

### 1. Depoyu Klonlayın ve Proje Dizinine Geçin

```bash
git clone <depo_url>
cd katilim-bankaciligi-kampanya-analizi
```

### 2. Sanal Ortam Oluşturun ve Aktifleştirin

```bash
# Sanal ortam oluşturma
python3 -m venv venv

# Aktifleştirme (macOS / Linux)
source venv/bin/activate

# Aktifleştirme (Windows)
.\venv\Scripts\activate
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🤖 Yerel LLM (Ollama) Kurulumu ve Model İndirme

Sistem, bilgi çıkarımı ve semantik sınıflandırma işlemleri için yerel Ollama sunucusunu kullanır.

1. **Ollama'yı İndirin**: [ollama.com](https://ollama.com/) adresinden işletim sisteminize uygun olan sürümü indirip kurun.
2. **Ollama Sunucusunu Başlatın**:
   ```bash
   ollama serve
   ```
3. **Gerekli LLM Modelini İndirin**:
   Ajanın varsayılan olarak kullandığı `llama3.1:8b` modelini indirin:
   ```bash
   ollama pull llama3.1:8b
   ```

---

## 🚀 Projenin Çalıştırılması

Proje üç ana aşamadan oluşur: Veri toplama (Scraping), NLP Analizi (Pipeline) ve Görselleştirme (Streamlit). Bu işlemleri terminalden veya Streamlit arayüzünden gerçekleştirebilirsiniz.

### Seçenek A: Arayüz (Streamlit) ile Çalıştırma (Tavsiye Edilen)

Streamlit dashboard'u yerel ortamda çalıştırmak için aşağıdaki komutu kullanın:

```bash
PYTHONPATH=. streamlit run app/dashboard.py --server.port 8501 --server.address 127.0.0.1
```

Arayüz açıldıktan sonra **"⚙️ Veri Yönetimi"** sekmesine giderek:
1. **Veri Toplamayı Başlat** butonuyla tüm bankaların kampanyalarını çekebilir,
2. **Analiz Pipeline'ını Çalıştır** butonuyla verileri kural veya LLM tabanlı olarak işleyebilirsiniz.

### Seçenek B: Terminal (CLI) ile Adım Adım Çalıştırma

Eğer işlemleri terminal üzerinden arka planda yapmak isterseniz:

#### 1. BDDK Banka Listesini Çekin
```bash
python scraper/bddk_scraper.py
```

#### 2. Katılım Bankalarının Kampanyalarını Scrape Edin
```bash
python scraper/campaign_scraper.py
```

#### 3. NLP & Normalizasyon Pipeline'ını Çalıştırın
- **Kural Tabanlı (Hızlı Mod - LLM Kullanmadan)**:
  ```bash
  python run_pipeline.py 0 --no-llm
  ```
- **Yapay Zeka Modu (LLM ile Semantik Analiz - Ollama açık olmalıdır)**:
  ```bash
  python run_pipeline.py
  ```

---

## 🐳 Docker ile Konteynerize Kurulum

Tüm sistemi (Ollama sunucusu + Streamlit Dashboard uygulaması) tek bir docker-compose komutu ile ayağa kaldırabilirsiniz.

### Docker Compose'u Başlatın

```bash
docker-compose up --build -d
```

Bu komut:
1. `teknofest-ollama` konteynerini başlatır ve içine `llama3.1:8b` modelini otomatik olarak yükler.
2. `teknofest-app` konteynerini başlatarak Streamlit arayüzünü ayağa kaldırır.

Arayüze tarayıcınızdan **`http://localhost:8501`** adresinden erişebilirsiniz.

---

## 🧪 Testlerin Çalıştırılması

Ön işleme kurallarını ve finansal değer normalizasyonunu doğrulamak için yazılmış 27 adet birim testini çalıştırmak için:

```bash
pytest tests/ -v
```

---

## 📄 Lisans

Bu proje **Apache License 2.0** kapsamında lisanslanmıştır. Projenin açık kaynak kodlu bileşenleri ticari ve akademik kullanıma uygundur.
