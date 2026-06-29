# TEKNOFEST 2026 Yapay Zeka Dil Ajanları Yarışması - Teknik Gereksinimler ve Mimari Kılavuz

Bu doküman, **2026_TEKNOFEST_TYDA_SARTNAME_Ikinci_Senaryo_TR_1_FJbSZ.pdf** isimli resmi şartnamede yer alan "Yapay Zeka Dil Ajanları Yarışması (2. Senaryo)" kapsamındaki teknik beklentileri, problem tanımlarını, model yeteneklerini ve mimari standartları detaylandırmak amacıyla hazırlanmıştır.

---

## 1. Sistem Mimarisi ve Uçtan Uca Veri Akışı

Geliştirilecek olan Doğal Dil İşleme (NLP) tabanlı çözümün, katılım bankacılığına ait yapılandırılmamış kampanya metinlerini toplayıp işleyerek son kullanıcıya (banka çalışanları veya müşteriler) dashboard ve chatbot arayüzleri üzerinden sunması gerekmektedir. Uçtan uca sistem mimarisi temel olarak 5 ana katmandan oluşur:

```
[Veri Kaynakları (BDDK Katılım Bankaları)]
                  │
                  ▼ (Web Scraping / Python Veri Toplama)
        [Veri Ön İşleme Hattı]
                  │
                  ▼ (Normalizasyon & Temizleme)
   [Doğal Dil İşleme (NLP) & LLM Katmanı] ──► [Katılım Bankacılığı Ontolojisi]
                  │
                  ▼ (Yapılandırılmış Veri - JSON / SQL)
     [Analitik ve Karşılaştırma Motoru]
                  │
                  ▼
   [Arayüz Katmanı (Dashboard & Chatbot)]
```

---

## 2. Teknik Bileşenler ve Temel Beklentiler

### 2.1. Veri Toplama ve Web Scraping Hatları
Yarışmacıların, sistemin besleneceği veriyi bağımsız olarak toplaması gerekmektedir.
*   **Kapsam:** BDDK'nın resmi web sitesinde (`https://www.bddk.org.tr/Kurulus/Liste/77`) listelenen tüm Katılım Bankacılığı kuruluşlarının resmi web siteleri, kampanya sayfaları, ürün detay metinleri ve kart avantaj açıklamaları veri setine dahil edilmelidir.
*   **Yöntem:** Python tabanlı veri toplama kütüphaneleri (BeautifulSoup, Scrapy, Selenium vb.) kullanılarak otomatik veri kazıma (web scraping) boru hatları kurulmalıdır. Toplanan veriler, metin madenciliği süreçlerine uygun olacak şekilde meta verileriyle (banka adı, erişim tarihi, kampanya URL'si vb.) birlikte saklanmalıdır.

### 2.2. Veri Ön İşleme ve Normalizasyon (Data Preprocessing)
Doğal dilde yazılmış metinlerin model tarafından doğru anlamlandırılabilmesi için gelişmiş ön işleme adımlarının uygulanması şarttır. Bu süreçte özellikle finansal değerlerin standart formata dönüştürülmesi (Veri Normalizasyonu) kritik öneme sahiptir:
*   **Metin Temizleme:** HTML etiketlerinin temizlenmesi, noktalama işaretlerinin amaca uygun elenmesi ve büyük/küçük harf dönüşümleri.
*   **Finansal Değer Normalizasyonu:** Farklı yazım kurallarına sahip sayısal ve birimsel ifadeler ortak bir paydaya indirgenmelidir.
    *   *Örnek 1 (Oranlar):* `%2,05`, `% 2.05` ve `2.05%` ifadelerinin tamamı sayısal olarak `2.05` ve birim olarak `oran` şeklinde normalize edilmelidir.
    *   *Örnek 2 (Para Birimleri):* `500 TL`, `500` ve `500 Türk Lirası` ifadeleri ortak bir yapılandırılmış nesneye (`value: 500, currency: TRY`) dönüştürülmelidir.

### 2.3. Metin Analizi ve Katılım Bankacılığı Terminolojisi Uyumu
Sistemin geleneksel (konvensiyonel) bankacılık terimleri ile katılım bankacılığı terimleri arasındaki nüansları ayırt edebilecek semantik bir derinliğe sahip olması gerekmektedir. Model, faizsiz finans ilkelerine ait kavramları doğru sınıflandırmalıdır:

| Geleneksel Bankacılık Kavramı | Katılım Bankacılığı Karşılığı | Teknik Anlamlandırma Beklentisi |
| :--- | :--- | :--- |
| Faiz Oranı | **Kâr Payı Oranı** | Finansman işlemine konu olan mal/hizmet üzerinden oluşan ve faiz içermeyen oran yükü. |
| Kredi | **Finansman** | Müşterinin ihtiyaç duyduğu mal veya hizmetin banka aracılığıyla satın alınması süreci. |
| Kredi Maliyeti | **Finansman Maliyeti** | Toplam geri ödeme tutarı ve müşterinin katlandığı net maliyet yapısı. |
| Vadeli Hesap | **Katılım Fonu** | Kâr-zarar ortaklığına dayanan, fon sahipleri ile banka arasında paylaşılan hesap türü. |
| Faizsiz / Masrafsız Kredi | **Masrafsız Finansman** | Tahsis ücreti, dosya masrafı veya ek komisyon barındırmayan finansman ürünleri. |
| Kampanyalı Kredi | **Avantajlı Finansman** | Standart koşullara kıyasla daha düşük kâr payı veya ek ödül sunan yapılar. |

### 2.4. Finansal Bilgi Çıkarımı (Information Extraction) ve Sınıflandırma
NLP modeli, yapılandırılmamış kampanya metinlerinden Named Entity Recognition (NER), kural tabanlı yaklaşımlar veya Large Language Model (LLM) prompting teknikleri kullanarak aşağıdaki öznitelikleri (features) otomatik olarak çıkarmalıdır:
1.  **Banka Bilgisi:** Kampanyayı sunan kuruluş adı.
2.  **Finansman Bilgileri:** Kâr payı oranı, maksimum finansman tutarı, vade süresi (ay bazında), taksit sayısı, tahsis ücreti ve dosya masrafı bilgileri.
3.  **Kampanya Koşulları ve Süresi:** Geçerlilik tarihi (örn: *31 Aralık 2026*), katılım şartları.
4.  **Avantaj ve Ödül Yapısı:** İndirim oranları, alışveriş puanları, hediye çekleri (örn: *5.000 TL alışveriş çeki*).
5.  **Hedef Kitle / Segmentasyon:** Yeni müşteriler, mevcut müşteriler, maaş müşterileri veya belirli meslek gruplarına özel segment tanımları.

Model, bu verileri kullanarak kampanya metnini otomatik olarak kategorize etmelidir (**Kampanya Türü Belirleme**). Sınıflandırılması gereken temel kategoriler şunlardır:
*   İhtiyaç Finansmanı Kampanyası
*   Konut Finansmanı Kampanyası
*   Taşıt Finansmanı Kampanyası
*   Alışveriş Puanı / Kart Kampanyası
*   Yeni Müşteri Kampanyası
*   Yatırım Ürünü Kampanyası

---

## 3. Karşılaştırma Motoru ve Analitik Yetenekler

Yapılandırılmış veri formatına dönüştürülen finansal bilgiler, bir analitik motor aracılığıyla çapraz sorgulanabilir ve karşılaştırılabilir hale getirilmelidir. Karşılaştırma motoru en az aşağıdaki metrikleri hesaplayabilmeli ve sıralayabilmelidir:
*   **En Düşük Kâr Payı Oranı** sunan bankanın tespiti.
*   **En Yüksek Ödül / Avantaj Miktarını** (nakit puan, çeki vb.) sağlayan kampanyanın belirlenmesi.
*   **En Uzun Vade Seçeneğini** sunan finansman ürününün listelenmesi.
*   **En Düşük Masraf / Tahsis Ücreti** gerektiren alternatiflerin bulunması.

---

## 4. Kurum İçi (On-Premise) Çalışma ve Açık Kaynak Standartları

### 4.1. Veri Güvenliği ve Regülasyon Uyumu
Bankacılık regülasyonları ve veri güvenliği gereksinimleri nedeniyle, geliştirilen çözümün tamamen **On-Premise (Kurum İçi)** sunucularda çalışabilecek bir mimaride tasarlanması zorunludur:
*   **Dış Bağımlılık Yasağı:** Model, internete bağlı dış API servislerine (OpenAI, Anthropic vb.) bağımlı olmadan çalışmalıdır. Müşteri veri akışları kurum dışına çıkmamalıdır.
*   **Lokal Çalıştırılabilirlik:** Tercih edilen LLM'ler veya NLP modelleri, yerel GPU/CPU altyapılarında yüksek performansla çıkarım (inference) yapabilmelidir.

### 4.2. Açık Kaynak Kod Yaklaşımı
*   Sistem mimarisinde yer alan tüm kütüphaneler, framework'ler ve temel modeller açık kaynak kodlu olmalı; ölçekleme aşamasında lisans problemi yaratabilecek kapalı kaynaklı yapılar kullanılmamalıdır.
*   Yarışma bitiminde tüm proje kodlarının **Apache License 2.0** ile lisanslanarak Türkiye Açık Kaynak Platformu GitHub hesabı üzerinde paylaşılması taahhüt edilmektedir.

---

## 5. Teslim Edilmesi Gereken Teknik Çıktılar

Yarışma jürisine sunulacak ve değerlendirmeye tabi tutulacak teknik bileşenler şunlardır:
1.  **Çalışan Proje Kodu:** GitHub'a `BilisimVadisi2026` etiketi ile yüklenecek olan; veri ön işleme, bilgi çıkarımı, veri normalizasyonu, chatbot ve dashboard kodlarını içeren eksiksiz kaynak kod deposu.
2.  **Bağımlılıklar ve Kurulum Kılavuzu:** Projenin lokal veya kurum içi sunucuda ayağa kaldırılabilmesi için gerekli kütüphanelerin listesi (`requirements.txt` veya `environment.yml`) ve adım adım kurulum talimatları.
3.  **Veri Seti Bağlantısı:** Toplanan katılım bankacılığı metinlerinin ve oluşturulan yapılandırılmış veri tabanının indirilebileceği herkese açık bir veri seti bağlantısı.
4.  **Demo Videosu:** Maksimum 5 dakika uzunluğunda, sistemin uçtan uca çalışmasını, metinlerden bilgi çıkarım süreçlerini, dashboard analitiklerini ve chatbot'un soru-cevap yeteneğini gösteren ekran kaydı.
