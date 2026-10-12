import os
import json
import httpx
from typing import Optional, Dict, Any, List
from enum import Enum
from app.core.config import settings


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class LLMClient:
    """Multi-provider LLM client with unified interface."""

    def __init__(self):
        self.provider = LLMProvider(settings.llm_provider.lower())
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url
        self.model = settings.llm_model
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send chat completion request based on provider."""
        if self.provider == LLMProvider.OPENAI:
            return await self._chat_openai(messages, temperature, max_tokens)
        elif self.provider == LLMProvider.ANTHROPIC:
            return await self._chat_anthropic(messages, temperature, max_tokens)
        elif self.provider == LLMProvider.GEMINI:
            return await self._chat_gemini(messages, temperature, max_tokens)
        elif self.provider == LLMProvider.OLLAMA:
            return await self._chat_ollama(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _chat_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self._get_headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _chat_anthropic(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        # Convert to Anthropic format
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_msg,
            "messages": user_messages,
        }
        headers = self._get_headers()
        headers["anthropic-version"] = "2023-06-01"
        response = await self.client.post(
            f"{self.base_url}/v1/messages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    async def _chat_gemini(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        # Convert to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        response = await self.client.post(
            f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _chat_ollama(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": False,
        }
        response = await self.client.post(
            f"{self.base_url}/api/chat",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    async def classify(
        self,
        text: str,
        categories: List[str],
        instructions: str = "",
    ) -> Dict[str, Any]:
        """Classify text into categories with confidence and reasoning."""
        sep = ", "
        prompt = (
            f"{instructions}\n"
            f"Classify: {text}\n"
            f"Categories: {sep.join(categories)}\n"
            'Respond as JSON: {"category": "...", "confidence": 0.95, "reasoning": "..."}'
        )
        raw = await self.chat([
            {"role": "system", "content": "Respond only with valid JSON."},
            {"role": "user", "content": prompt},
        ], temperature=0.3)
        start, end = raw.find("{"), raw.rfind("}") + 1
        try:
            return json.loads(raw[start:end])
        except Exception:
            return {"category": "unknown", "confidence": 0.0, "reasoning": raw}

    async def generate(
        self,
        prompt: str,
        system: str = "You are a helpful AI assistant.",
        temperature: float = 0.7,
    ) -> str:
        """Generate text from prompt."""
        return await self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ], temperature=temperature)


async def get_llm_client() -> LLMClient:
    client = LLMClient()
    try:
        yield client
    finally:
        await client.close()