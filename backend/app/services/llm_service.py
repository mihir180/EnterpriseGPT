"""
Modular LLM service.

Design goal: every route in this app calls `llm_service.generate_answer(...)`
and never cares which provider is actually serving the request. Swapping
providers is a one-line change in `.env` (LLM_PROVIDER=ollama|openai|gemini) -
no code changes anywhere else.

Default provider is Ollama: a local inference server (https://ollama.com)
that runs open models (Llama 3, Mistral, Qwen, ...) entirely on your own
machine. No API key, no per-token billing, no internet call at inference
time - ideal for a first working RAG system and for privacy-sensitive
enterprise data that shouldn't leave the network.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMError(Exception):
    """Raised when the configured LLM provider fails to produce an answer."""


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Return the model's raw text answer."""
        raise NotImplementedError


class OllamaProvider(BaseLLMProvider):
    """
    Calls a local Ollama server's /api/chat endpoint.

    Requires Ollama to be installed and running, with the configured model
    pulled ahead of time (see README: "Local LLM setup (Ollama)").
    No API key is used or required.
    """

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout_seconds

    async def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMError(
                "Could not reach Ollama at "
                f"{self.base_url}. Is Ollama running? (see README setup)."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"Ollama returned an error ({exc.response.status_code}). "
                f"Is the model '{self.model}' pulled? Run: ollama pull {self.model}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMError("Ollama request timed out. Try a smaller model or increase "
                            "OLLAMA_TIMEOUT_SECONDS.") from exc

        data = response.json()
        message = data.get("message", {})
        content = message.get("content", "")
        if not content:
            raise LLMError("Ollama returned an empty response.")
        return content.strip()


class OpenAIProvider(BaseLLMProvider):
    """
    Cloud fallback using the OpenAI Chat Completions API.
    Only instantiated/used if LLM_PROVIDER=openai and OPENAI_API_KEY is set.
    """

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise LLMError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set in .env."
            )
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model

    async def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"OpenAI API error: {exc.response.text}") from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise LLMError("Unexpected OpenAI response shape.") from exc


class GeminiProvider(BaseLLMProvider):
    """
    Cloud fallback using the Gemini API.
    Only instantiated/used if LLM_PROVIDER=gemini and GEMINI_API_KEY is set.
    """

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise LLMError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set in .env."
            )
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model

    async def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"Gemini API error: {exc.response.text}") from exc

        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            raise LLMError("Unexpected Gemini response shape.") from exc


def _build_provider() -> BaseLLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        return OllamaProvider()
    if provider == "openai":
        return OpenAIProvider()
    if provider == "gemini":
        return GeminiProvider()
    raise LLMError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'. "
                    "Use 'ollama', 'openai', or 'gemini'.")


class LLMService:
    """
    Facade used by the rest of the app. Lazily builds the configured
    provider so import-time never fails even if e.g. an API key is missing
    for a provider that isn't actually selected.
    """

    def __init__(self) -> None:
        self._provider: BaseLLMProvider | None = None

    def _get_provider(self) -> BaseLLMProvider:
        if self._provider is None:
            self._provider = _build_provider()
        return self._provider

    async def generate_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        provider = self._get_provider()
        return await provider.generate_answer(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=max_tokens if max_tokens is not None else settings.llm_max_tokens,
        )


llm_service = LLMService()
