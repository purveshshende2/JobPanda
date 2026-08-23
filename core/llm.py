"""Minimal OpenAI-compatible chat client (works with OpenAI, Groq, Ollama, etc.)."""
import os
import re

import requests


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = (api_key or "").strip()
        base = (base_url or "").strip().strip('"').rstrip("/")
        # tolerate users pasting the full endpoint URL
        if base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")]
        self.base_url = base
        self.model = (model or "").strip()

    @classmethod
    def from_env(cls, api_key=None, base_url=None, model=None):
        return cls(
            api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
            base_url=base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )

    def list_models(self) -> list:
        """Fetch model IDs available to this key (OpenAI-compatible /models)."""
        resp = requests.get(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return sorted(m.get("id", "?") for m in data.get("data", []))

    @property
    def configured(self) -> bool:
        return bool(self.api_key or "localhost" in self.base_url or "127.0.0.1" in self.base_url)

    def chat(self, system: str, user: str, temperature: float = 0.4, max_tokens: int | None = None) -> str:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        if resp.status_code >= 400:
            hint = {
                401: "API key is invalid or expired.",
                403: "Key lacks access to this model (or region blocked).",
                404: f"Endpoint not found - check Base URL. Expected something like https://api.groq.com/openai/v1 (you sent to {self.base_url}).",
                429: "Rate limit reached - wait a moment and retry.",
            }.get(resp.status_code, "")
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}{' — ' + hint if hint else ''}")
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        # reasoning models (Qwen3, DeepSeek-R1...) emit <think> blocks - strip them
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return content
