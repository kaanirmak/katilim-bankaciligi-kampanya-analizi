"""
TEKNOFEST 2026 - Yerel LLM İstemcisi (Ollama Entegrasyonu)

On-Premise çalışma zorunluluğuna uygun olarak, tüm LLM çıkarımları
yerel sunucularda Ollama üzerinden gerçekleştirilir.
Harici API servisleri (OpenAI, Anthropic vb.) kullanılmaz.
"""

import json
import os
from typing import Any, Optional

from loguru import logger

try:
    import ollama
except ImportError:
    ollama = None
    logger.warning(
        "Ollama kütüphanesi bulunamadı. 'pip install ollama' ile yükleyin."
    )


# Varsayılan model konfigürasyonu
DEFAULT_CONFIG = {
    "model": "llama3.1:8b",       # Varsayılan model
    "host": os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),  # Ollama sunucu adresi
    "temperature": 0.1,            # Düşük sıcaklık = daha deterministik
    "top_p": 0.9,
    "num_predict": 2048,           # Maksimum token sayısı
}

# Alternatif model önerileri (Türkçe performansa göre)
RECOMMENDED_MODELS = {
    "llama3.1:8b": "Meta Llama 3.1 8B - İyi Türkçe desteği, dengeli performans",
    "llama3.2:3b": "Meta Llama 3.2 3B - Hafif model, hızlı çıkarım",
    "mistral:7b": "Mistral 7B - İyi genel performans",
    "qwen2.5:7b": "Qwen 2.5 7B - Güçlü çok dilli destek",
    "gemma2:9b": "Google Gemma 2 9B - İyi yapılandırılmış çıktı",
}


class LLMClient:
    """Yerel LLM istemcisi (Ollama tabanlı).

    Katılım bankacılığı metinlerinden bilgi çıkarımı,
    sınıflandırma ve soru-cevap işlemleri için kullanılır.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """LLMClient'ı başlat.

        Args:
            model: Kullanılacak Ollama model adı.
            host: Ollama sunucu adresi.
            temperature: Çıkarım sıcaklığı (0-1).
        """
        self.model = model or DEFAULT_CONFIG["model"]
        self.host = host or DEFAULT_CONFIG["host"]
        self.temperature = temperature or DEFAULT_CONFIG["temperature"]
        self._client = None
        self._available = False

        self._initialize_client()

    def _initialize_client(self):
        """Ollama istemcisini başlat ve bağlantıyı kontrol et."""
        if ollama is None:
            logger.error("Ollama kütüphanesi yüklü değil.")
            return

        try:
            self._client = ollama.Client(host=self.host)
            # Bağlantı testi
            models = self._client.list()
            available_models = [m.model for m in models.models]
            logger.info(f"Ollama bağlantısı başarılı. Mevcut modeller: {available_models}")

            if self.model not in available_models:
                logger.warning(
                    f"Model '{self.model}' bulunamadı. "
                    f"'ollama pull {self.model}' komutu ile indirin."
                )
            else:
                self._available = True
                logger.info(f"LLM hazır: {self.model}")
        except Exception as e:
            logger.error(f"Ollama sunucusuna bağlanılamadı: {e}")
            logger.info("Ollama sunucusunu başlatmak için: 'ollama serve'")

    @property
    def is_available(self) -> bool:
        """LLM'in kullanılabilir olup olmadığını kontrol et."""
        return self._available

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
    ) -> Optional[str]:
        """LLM'den metin üret.

        Args:
            prompt: Kullanıcı prompt'u.
            system_prompt: Sistem prompt'u (rol tanımı).
            temperature: Çıkarım sıcaklığı override.
            json_mode: JSON formatında çıktı isteyip istememe.

        Returns:
            LLM yanıtı veya None (hata durumunda).
        """
        if not self._available:
            logger.error("LLM kullanılabilir değil. generate() çağrısı atlandı.")
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        options = {
            "temperature": temperature or self.temperature,
            "top_p": DEFAULT_CONFIG["top_p"],
            "num_predict": DEFAULT_CONFIG["num_predict"],
        }

        try:
            response = self._client.chat(
                model=self.model,
                messages=messages,
                options=options,
                format="json" if json_mode else "",
            )
            result = response.message.content
            logger.debug(
                f"LLM yanıt uzunluğu: {len(result)} karakter | "
                f"Model: {self.model}"
            )
            return result
        except Exception as e:
            logger.error(f"LLM çıkarım hatası: {e}")
            return None

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Optional[dict]:
        """LLM'den JSON formatında yanıt al.

        Args:
            prompt: Kullanıcı prompt'u.
            system_prompt: Sistem prompt'u.

        Returns:
            Parse edilmiş JSON sözlüğü veya None.
        """
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
        )
        if response is None:
            return None

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("LLM yanıtı JSON olarak parse edilemedi. Temizleme deneniyor...")
            # JSON bloğunu metinden çıkarmayı dene
            try:
                start = response.index("{")
                end = response.rindex("}") + 1
                return json.loads(response[start:end])
            except (ValueError, json.JSONDecodeError):
                logger.error(f"JSON parse başarısız: {response[:200]}...")
                return None


# Modül seviyesinde singleton
_llm_client: Optional[LLMClient] = None


def get_llm_client(**kwargs) -> LLMClient:
    """Global LLMClient instance'ını döndür."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(**kwargs)
    return _llm_client
