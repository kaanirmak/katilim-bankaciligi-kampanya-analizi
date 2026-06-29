"""
TEKNOFEST 2026 - Metin Temizleme Modülü

HTML etiketlerini temizler, gereksiz karakterleri kaldırır
ve metin standardizasyonu uygular.
"""

import re
import unicodedata
from typing import Optional

from bs4 import BeautifulSoup
from loguru import logger


def remove_html_tags(text: str) -> str:
    """HTML etiketlerini metinden kaldır.

    Args:
        text: HTML içerebilen ham metin.

    Returns:
        HTML etiketlerinden arındırılmış temiz metin.
    """
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def normalize_whitespace(text: str) -> str:
    """Boşlukları ve satır sonlarını normalize et.

    Args:
        text: Normalize edilecek metin.

    Returns:
        Tek boşluklu, temiz metin.
    """
    # Çoklu boşlukları tek boşluğa dönüştür
    text = re.sub(r"\s+", " ", text)
    # Başındaki ve sonundaki boşlukları kaldır
    return text.strip()


def normalize_unicode(text: str) -> str:
    """Unicode karakterleri NFC formuna normalize et.

    Türkçe karakterlerin (ç, ğ, ı, ö, ş, ü) doğru temsil
    edilmesini sağlar.

    Args:
        text: Normalize edilecek metin.

    Returns:
        NFC formunda normalize edilmiş metin.
    """
    return unicodedata.normalize("NFC", text)


def fix_turkish_encoding(text: str) -> str:
    """Yaygın Türkçe karakter encoding hatalarını düzelt.

    Args:
        text: Encoding hataları içerebilen metin.

    Returns:
        Düzeltilmiş metin.
    """
    replacements = {
        "Ã¼": "ü",
        "Ã§": "ç",
        "Ã¶": "ö",
        "Ä±": "ı",
        "ÅŸ": "ş",
        "Äž": "Ğ",
        "Ä°": "İ",
        "Ãœ": "Ü",
        "Ã‡": "Ç",
        "Ã–": "Ö",
        "Åž": "Ş",
    }
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    return text


def remove_special_characters(text: str, keep_punctuation: bool = True) -> str:
    """Özel karakterleri kaldır.

    Args:
        text: Temizlenecek metin.
        keep_punctuation: True ise temel noktalama işaretlerini koru.

    Returns:
        Temizlenmiş metin.
    """
    if keep_punctuation:
        # Türkçe harfler, rakamlar, temel noktalama ve boşluk koru
        pattern = r"[^a-zA-ZçÇğĞıİöÖşŞüÜâÂîÎûÛ0-9\s.,;:!?%€₺$()/-]"
    else:
        # Sadece Türkçe harfler, rakamlar ve boşluk
        pattern = r"[^a-zA-ZçÇğĞıİöÖşŞüÜâÂîÎûÛ0-9\s]"

    return re.sub(pattern, " ", text)


def normalize_case(text: str, mode: str = "lower") -> str:
    """Büyük/küçük harf dönüşümü uygula.

    Türkçe'ye özgü I/ı ve İ/i dönüşümlerini doğru yapar.

    Args:
        text: Dönüştürülecek metin.
        mode: "lower" veya "upper".

    Returns:
        Dönüştürülmüş metin.
    """
    if mode == "lower":
        # Türkçe'ye özel: I → ı (İngilizce'de I → i olur)
        text = text.replace("I", "ı").replace("İ", "i")
        return text.lower()
    elif mode == "upper":
        text = text.replace("i", "İ").replace("ı", "I")
        return text.upper()
    return text


def remove_urls(text: str) -> str:
    """URL'leri metinden kaldır.

    Args:
        text: URL içerebilen metin.

    Returns:
        URL'lerden arındırılmış metin.
    """
    url_pattern = r"https?://\S+|www\.\S+"
    return re.sub(url_pattern, "", text)


def remove_email_addresses(text: str) -> str:
    """E-posta adreslerini metinden kaldır.

    Args:
        text: E-posta adresi içerebilen metin.

    Returns:
        E-posta adreslerinden arındırılmış metin.
    """
    email_pattern = r"\S+@\S+\.\S+"
    return re.sub(email_pattern, "", text)


def clean_text(
    text: str,
    remove_html: bool = True,
    fix_encoding: bool = True,
    remove_urls_flag: bool = True,
    remove_emails: bool = True,
    keep_punctuation: bool = True,
    lowercase: bool = False,
) -> str:
    """Tam metin temizleme pipeline'ı.

    Args:
        text: Temizlenecek ham metin.
        remove_html: HTML etiketlerini kaldır.
        fix_encoding: Türkçe encoding hatalarını düzelt.
        remove_urls_flag: URL'leri kaldır.
        remove_emails: E-posta adreslerini kaldır.
        keep_punctuation: Temel noktalama işaretlerini koru.
        lowercase: Küçük harfe dönüştür.

    Returns:
        Temizlenmiş metin.
    """
    if not text:
        return ""

    # Adım 1: Unicode normalize
    text = normalize_unicode(text)

    # Adım 2: Encoding düzeltme
    if fix_encoding:
        text = fix_turkish_encoding(text)

    # Adım 3: HTML kaldırma
    if remove_html:
        text = remove_html_tags(text)

    # Adım 4: URL kaldırma
    if remove_urls_flag:
        text = remove_urls(text)

    # Adım 5: E-posta kaldırma
    if remove_emails:
        text = remove_email_addresses(text)

    # Adım 6: Özel karakter temizleme
    text = remove_special_characters(text, keep_punctuation=keep_punctuation)

    # Adım 7: Boşluk normalizasyonu
    text = normalize_whitespace(text)

    # Adım 8: Küçük harf dönüşümü (opsiyonel)
    if lowercase:
        text = normalize_case(text, mode="lower")

    return text


def clean_campaign_data(campaign: dict) -> dict:
    """Kampanya verisinin metin alanlarını temizle.

    Args:
        campaign: Ham kampanya verisi sözlüğü.

    Returns:
        Temizlenmiş kampanya verisi sözlüğü.
    """
    cleaned = campaign.copy()

    text_fields = ["title", "full_text", "meta_description", "listing_title"]
    for field in text_fields:
        if field in cleaned and cleaned[field]:
            cleaned[field] = clean_text(cleaned[field])

    if "paragraphs" in cleaned:
        cleaned["paragraphs"] = [
            clean_text(p) for p in cleaned["paragraphs"] if clean_text(p)
        ]

    logger.debug(f"Kampanya temizlendi: {cleaned.get('title', 'N/A')[:50]}")
    return cleaned
