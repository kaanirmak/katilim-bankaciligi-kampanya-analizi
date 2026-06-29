"""
TEKNOFEST 2026 - Streamlit Dashboard

Katılım bankacılığı kampanyalarını görselleştiren,
karşılaştıran ve RAG tabanlı Chatbot ile soru-cevap sunan
interaktif web uygulaması.
"""

import json
from pathlib import Path
import streamlit as st
import pandas as pd

from analytics.comparison_engine import ComparisonEngine
from nlp.llm_client import get_llm_client
from nlp.prompts.extraction import SYSTEM_PROMPT_CHATBOT, CHATBOT_PROMPT_TEMPLATE

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="Katılım Bankacılığı Kampanya Analizi",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS ile özel premium stil (Göz alıcı HSL renkler ve cam morfolojisi)
st.markdown("""
<style>
    .reportview-container {
        background: #0f172a;
    }
    .metric-card {
        background-color: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        text-align: center;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)


def load_data() -> list[dict]:
    """İşlenmiş kampanya verilerini yükle."""
    consolidated_file = Path("data/processed/processed_campaigns.json")
    if consolidated_file.exists():
        try:
            with open(consolidated_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("campaigns", [])
        except Exception as e:
            st.error(f"Veri yüklenirken hata oluştu: {e}")
            
    # Alternatif olarak tüm processed_campaigns_*.json dosyalarını tara
    data_path = Path("data/processed")
    campaigns = []
    if data_path.exists():
        for json_file in data_path.glob("processed_campaigns_*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "campaigns" in data:
                        campaigns.extend(data["campaigns"])
            except Exception:
                pass
    return campaigns


def render_sidebar(campaigns: list[dict]):
    """Sol panel: Filtreler ve ayarlar."""
    st.sidebar.title("🏦 Filtre Paneli")
    st.sidebar.markdown("Kampanyaları filtrelemek ve sıralamak için kullanın.")

    # Benzersiz banka listesi
    available_banks = sorted(list(set(c.get("bank_name", "Bilinmeyen") for c in campaigns if c.get("bank_name"))))
    banks = ["Tümü"] + available_banks
    selected_bank = st.sidebar.selectbox("Banka Seçimi", banks)

    # Kategori listesi
    available_cats = sorted(list(set(c.get("final_category_name", "Bilinmeyen") for c in campaigns if c.get("final_category_name"))))
    categories = ["Tümü"] + available_cats
    selected_category = st.sidebar.selectbox("Kampanya Türü", categories)

    st.sidebar.subheader("Sıralama")
    sort_options = {
        "En Yüksek Ödül Tutarı": "reward",
        "En Düşük Kâr Payı Oranı": "rate",
        "En Uzun Vade": "maturity",
        "En Düşük Tahsis Masrafı": "fee",
    }
    selected_sort_label = st.sidebar.selectbox("Sıralama Kriteri", list(sort_options.keys()))
    selected_sort = sort_options[selected_sort_label]

    return selected_bank, selected_category, selected_sort


def get_rag_context(query: str, campaigns: list[dict], max_results: int = 3) -> str:
    """Kullanıcı sorusuyla en alakalı kampanyaları bulup context hazırlar."""
    query_lower = query.lower()
    scored_campaigns = []
    
    for c in campaigns:
        score = 0
        text = (c.get("title", "") + " " + c.get("full_text", "")).lower()
        
        # Basit keyword eşleme skoru
        for word in query_lower.split():
            if len(word) > 2 and word in text:
                score += 1
                
        # Kategori keyword eşleşirse ek puan
        cat_name = c.get("final_category_name", "").lower()
        if cat_name and any(w in cat_name for w in query_lower.split()):
            score += 2
            
        if score > 0:
            scored_campaigns.append((score, c))
            
    # Skora göre sırala
    scored_campaigns.sort(key=lambda x: x[0], reverse=True)
    top_campaigns = [item[1] for item in scored_campaigns[:max_results]]
    
    # Eğer hiç eşleşme bulunamazsa varsayılan olarak ilk birkaç kampanyayı ekle
    if not top_campaigns:
        top_campaigns = campaigns[:max_results]
        
    context = ""
    for i, c in enumerate(top_campaigns, 1):
        context += f"--- Kampanya {i} ---\n"
        context += f"Banka: {c.get('bank_name', 'Bilinmeyen')}\n"
        context += f"Başlık: {c.get('title', 'Başlıksız')}\n"
        context += f"Kategori: {c.get('final_category_name', 'Bilinmeyen')}\n"
        
        summary = c.get("summary", {})
        rates = summary.get("rates", [])
        amounts = summary.get("amounts", [])
        durations = summary.get("durations", [])
        
        if rates:
            context += f"Kâr Payı Oranı: %{rates[0].get('value')}\n"
        if amounts:
            context += f"Tutar: {amounts[0].get('value')} {amounts[0].get('currency')}\n"
        if durations:
            context += f"Vade/Süre: {durations[0].get('value')} {durations[0].get('unit')}\n"
            
        llm_data = c.get("llm_based", {})
        if llm_data and llm_data.get("conditions"):
            context += f"Koşullar: {', '.join(llm_data['conditions'][:3])}\n"
            
        context += f"Detaylı Metin: {c.get('full_text', '')[:300]}...\n\n"
        
    return context


def render_main_dashboard(campaigns: list[dict], selected_bank: str, selected_category: str, selected_sort: str):
    """Ana dashboard sayfası."""
    st.title("🏦 Katılım Bankacılığı Kampanya Analiz Paneli")
    st.markdown(
        "Katılım bankalarına ait güncel kampanya metinlerinin semantik analizleri, normalleştirilmiş değerleri ve karşılaştırmaları."
    )

    if not campaigns:
        st.warning("⚠️ Henüz işlenmiş kampanya verisi bulunamadı. Lütfen scraper ve pipeline modüllerini çalıştırın.")
        return

    # Engine başlat ve yükle
    engine = ComparisonEngine()
    engine.load_campaigns(campaigns)

    # Filtreleme uygulaması
    filtered_campaigns = campaigns
    if selected_bank != "Tümü":
        filtered_campaigns = [c for c in filtered_campaigns if c.get("bank_name") == selected_bank]
    if selected_category != "Tümü":
        filtered_campaigns = [c for c in filtered_campaigns if c.get("final_category_name") == selected_category]

    # Metrik hesaplamaları
    tot_campaigns = len(filtered_campaigns)
    
    # En düşük kâr payı
    min_rate_val = "—"
    rates_list = []
    for c in filtered_campaigns:
        rates = c.get("summary", {}).get("rates", [])
        if rates:
            rates_list.append(min(r["value"] for r in rates))
    if rates_list:
        min_rate_val = f"%{min(rates_list):.2f}"

    # Maksimum vade
    max_duration_val = "—"
    duration_list = []
    for c in filtered_campaigns:
        durs = c.get("summary", {}).get("durations", [])
        month_durs = [d["value"] for d in durs if d.get("unit") == "month"]
        if month_durs:
            duration_list.append(max(month_durs))
    if duration_list:
        max_duration_val = f"{max(duration_list)} ay"

    # Maksimum avantaj/ödül
    max_reward_val = "—"
    reward_list = []
    for c in filtered_campaigns:
        llm_data = c.get("llm_based", {})
        if llm_data and llm_data.get("rewards"):
            for rew in llm_data["rewards"]:
                if rew.get("value"):
                    reward_list.append(rew["value"])
    if reward_list:
        max_reward_val = f"{max(reward_list):,.0f} TL"

    # Metrik Kartlarını Göster
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{tot_campaigns}</div><div class="metric-label">Toplam Kampanya</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{min_rate_val}</div><div class="metric-label">En Düşük Kâr Payı</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{max_duration_val}</div><div class="metric-label">Maksimum Vade</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{max_reward_val}</div><div class="metric-label">En Yüksek Ödül</div></div>', unsafe_allow_html=True)

    st.divider()

    # Çapraz sıralı liste
    st.subheader(f"📋 Kampanya Karşılaştırma Listesi (Sıralama: {selected_sort.upper()})")
    
    # Karşılaştırma motorunu çalıştır
    category_filter = None if selected_category == "Tümü" else selected_category
    sorted_results = engine.compare_banks(metric=selected_sort, category=category_filter)
    
    if sorted_results:
        df = pd.DataFrame(sorted_results)
        # Sütun isimlerini Türkçeleştir
        column_mapping = {
            "bank_name": "Banka",
            "campaign_title": "Kampanya Başlığı",
            "rate_value": "Kâr Payı Oranı (%)",
            "rate_raw": "Oran Metni",
            "category": "Kategori",
            "amount_value": "Tutar",
            "currency": "Para Birimi",
            "amount_raw": "Tutar Metni",
            "maturity_months": "Vade (Ay)",
            "maturity_raw": "Vade Metni",
            "fee_value": "Tahsis Ücreti",
            "is_free": "Masrafsız mı?"
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Bu kriterlere uygun detaylı finansal verisi olan kampanya bulunamadı. Genel kampanya listesi aşağıdadır.")

    # Detaylı Kart Görünümü
    st.subheader("🔍 Tüm Kampanya Detayları")
    for c in filtered_campaigns:
        with st.expander(f"🏦 {c.get('bank_name')} - {c.get('title')}"):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("**Kampanya Metni:**")
                st.write(c.get("full_text")[:800] + "..." if len(c.get("full_text", "")) > 800 else c.get("full_text"))
                
                # Koşullar
                llm_data = c.get("llm_based", {})
                if llm_data and llm_data.get("conditions"):
                    st.markdown("**Katılım Koşulları:**")
                    for cond in llm_data["conditions"]:
                        st.write(f"- {cond}")
            with c2:
                st.markdown("**Sınıflandırma:**")
                st.info(f"🏷️ {c.get('final_category_name')} (Güven: {c.get('final_confidence', 0):.0%})")
                
                st.markdown("**Tespit Edilen Finansal Değerler:**")
                summary = c.get("summary", {})
                rates = summary.get("rates", [])
                amounts = summary.get("amounts", [])
                durations = summary.get("durations", [])
                dates = summary.get("dates", [])
                
                if rates:
                    st.success(f"📈 Kâr Payı Oranı: %{rates[0]['value']}")
                if amounts:
                    st.success(f"💰 Tutar: {amounts[0]['value']:,} {amounts[0].get('currency')}")
                if durations:
                    st.success(f"⏱️ Süre: {durations[0]['value']} {durations[0].get('unit')}")
                if dates:
                    st.success(f"📅 Son Geçerlilik: {dates[-1]['value']}")
                    
                st.markdown(f"[Kampanya Sayfasına Git]({c.get('url')})")


def render_chatbot_tab(campaigns: list[dict]):
    """Chatbot sekmesi (Local RAG entegrasyonu ile)."""
    st.subheader("💬 RAG Tabanlı Kampanya Asistanı")
    st.markdown(
        "Sistemdeki tüm katılım bankacılığı kampanyalarını sorgulamak için bu asistanı kullanabilirsiniz. "
        "Sorularınız yerel veritabanında taranacak ve tamamen yerel LLM (Ollama) tarafından cevaplandırılacaktır."
    )

    # LLM İstemcisini kontrol et
    llm = get_llm_client()
    if not llm.is_available:
        st.error("⚠️ Yerel LLM sunucusuna (Ollama) bağlanılamadı. Lütfen Ollama sunucusunun çalıştığından emin olun.")
        return

    st.success(f"🟢 Yerel LLM Bağlantısı Aktif: {llm.model}")

    # Sohbet geçmişi
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": (
                    "Merhaba! Ben katılım bankacılığı kampanya danışmanıyım. "
                    "Kuveyt Türk, Vakıf Katılım, Albaraka veya diğer katılım bankalarının "
                    "kampanyaları ve kâr payı oranları hakkında bana soru sorabilirsiniz."
                ),
            }
        ]

    # Geçmiş mesajları render et
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Kullanıcı girişi
    if user_query := st.chat_input("Örn: En yüksek nakit iade veren kampanya hangisi?"):
        st.session_state.chat_messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # RAG Context oluştur
        with st.spinner("İlgili kampanyalar sorgulanıyor ve cevap hazırlanıyor..."):
            context = get_rag_context(user_query, campaigns)
            
            prompt = CHATBOT_PROMPT_TEMPLATE.format(
                user_question=user_query,
                context_data=context,
            )
            
            # Ollama'dan yanıt al
            response = llm.generate(prompt=prompt, system_prompt=SYSTEM_PROMPT_CHATBOT)
            
            if not response:
                response = "Üzgünüm, Ollama sunucusundan yanıt alınamadı."

        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)
            
        with st.expander("📚 RAG Kaynak Verisi (LLM'e gönderilen bağlam)"):
            st.code(context)


class StreamlitLogSink:
    """Streamlit arayüzüne log satırlarını aktaran sink sınıfı."""

    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.logs = []

    def write(self, message):
        clean_msg = message.strip()
        if clean_msg:
            self.logs.append(clean_msg)
            # Son 25 log satırını göster
            self.placeholder.code("\n".join(self.logs[-25:]))


def render_management_tab():
    """Veri Toplama ve Analiz Yönetimi sekmesi."""
    st.subheader("⚙️ Veri Toplama ve Analiz Yönetimi")
    st.markdown(
        "Katılım bankalarından canlı veri çekebilir ve NLP/LLM analiz pipeline'ını buradan başlatabilirsiniz."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 1. Web Scraping (Veri Toplama)")
        st.markdown("BDDK listesindeki bankaların kampanya sayfalarından veriler indirilir.")

        from scraper.config import KATILIM_BANKALARI
        bank_names = {k: v["name"] for k, v in KATILIM_BANKALARI.items()}
        selected_scrape_bank = st.selectbox(
            "Scrape Edilecek Banka",
            ["Tümü"] + list(bank_names.values()),
            key="scrape_bank_select",
        )

        scrape_button = st.button("🔍 Veri Toplamayı Başlat", use_container_width=True)

    with c2:
        st.markdown("### 2. NLP & Normalizasyon Pipeline")
        st.markdown(
            "İndirilen ham veriler temizlenir, normalleştirilir ve yerel LLM (Ollama) ile analiz edilir."
        )

        limit_val = st.number_input(
            "İşlenecek Kampanya Limiti (Hızlı test için, 0=Sınırsız)",
            min_value=0,
            value=0,
        )
        use_llm_opt = st.checkbox("🤖 Yapay Zeka (LLM) Analizini Etkinleştir (Yavaş)", value=False)
        pipeline_button = st.button("🚀 Analiz Pipeline'ını Çalıştır", use_container_width=True)

    log_header = st.empty()
    log_placeholder = st.empty()

    if scrape_button:
        log_header.markdown("### 📝 Canlı Log Akışı (Veri Toplama)")
        log_sink = StreamlitLogSink(log_placeholder)
        from loguru import logger
        sink_id = logger.add(
            log_sink.write,
            format="{time:HH:mm:ss} | {level} | {message}",
            colorize=False,
        )

        try:
            from scraper.campaign_scraper import run_campaign_scraper

            # Seçilen banka ID'sini bul
            target_ids = None
            if selected_scrape_bank != "Tümü":
                target_ids = [
                    k for k, v in KATILIM_BANKALARI.items() if v["name"] == selected_scrape_bank
                ]

            logger.info(f"Seçilen bankalar için scraper başlatılıyor: {selected_scrape_bank}")
            summary = run_campaign_scraper(bank_ids=target_ids)
            logger.info(f"Scraping tamamlandı! Özet: {summary}")
            st.success("✅ Veri toplama başarıyla tamamlandı!")
        except Exception as e:
            logger.error(f"Scraping sırasında hata: {e}")
            st.error(f"Hata oluştu: {e}")
        finally:
            logger.remove(sink_id)

    if pipeline_button:
        log_header.markdown("### 📝 Canlı Log Akışı (NLP & LLM)")
        log_sink = StreamlitLogSink(log_placeholder)
        from loguru import logger
        sink_id = logger.add(
            log_sink.write,
            format="{time:HH:mm:ss} | {level} | {message}",
            colorize=False,
        )

        try:
            import importlib
            import run_pipeline
            importlib.reload(run_pipeline)

            logger.info(f"Pipeline {limit_val} limit değeri ile başlatılıyor (LLM={use_llm_opt})...")
            run_pipeline.run_pipeline(limit=limit_val, force_no_llm=not use_llm_opt)
            logger.info("Pipeline başarıyla tamamlandı!")
            st.success("✅ NLP ve normalizasyon pipeline'ı tamamlandı! Sayfayı yenileyerek yeni verileri görebilirsiniz.")
            st.button("🔄 Verileri Yeniden Yükle")
        except Exception as e:
            logger.error(f"Pipeline hatası: {e}")
            st.error(f"Hata oluştu: {e}")
        finally:
            logger.remove(sink_id)


def main():
    """Ana giriş noktası."""
    campaigns = load_data()
    selected_bank, selected_category, selected_sort = render_sidebar(campaigns)

    tab1, tab2, tab3 = st.tabs(
        ["📊 Karşılaştırma Paneli", "💬 Akıllı Asistan (RAG)", "⚙️ Veri Yönetimi"]
    )

    with tab1:
        render_main_dashboard(campaigns, selected_bank, selected_category, selected_sort)

    with tab2:
        render_chatbot_tab(campaigns)

    with tab3:
        render_management_tab()


if __name__ == "__main__":
    main()
