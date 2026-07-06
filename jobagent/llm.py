"""A tiny LLM client for any OpenAI-compatible endpoint.

The default target is a local Ollama server: no API key, runs offline, free.
The exact same client works against OpenAI, Groq, Together, etc. — just change
the base_url / model / api_key. We use `requests` only, so there is no heavy
vendor SDK to install or keep up to date.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests


class LLMError(RuntimeError):
    """Raised when the model endpoint is unreachable or returns garbage."""


@dataclass
class LLMClient:
    base_url: str = "http://localhost:11434/v1"
    model: str = "llama3.1"
    api_key: str | None = None
    timeout: int = 120

    @property
    def available(self) -> bool:
        """Best-effort reachability check so callers can degrade gracefully."""
        root = self.base_url.rstrip("/").removesuffix("/v1")
        try:
            requests.get(root, timeout=3)
            return True
        except requests.RequestException:
            return False

    def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise LLMError(f"LLM request failed ({url}): {exc}") from exc
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected LLM response shape: {data}") from exc

    def chat_json(self, system: str, user: str, temperature: float = 0.2) -> dict:
        """Ask for a single JSON object and parse it defensively."""
        guard = (
            "\n\nReturn a single valid JSON object and nothing else. "
            "No markdown fences, no commentary before or after."
        )
        return _extract_json(self.chat(system + guard, user, temperature))


def _extract_json(text: str) -> dict:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise LLMError(f"Could not parse JSON from model output: {text[:200]}...")
