"""
Ollama LLM provider — calls a local Ollama instance via HTTP.

Environment variables:
    OLLAMA_BASE_URL  default: http://localhost:11434
    OLLAMA_MODEL     default: llama3.2:3b
    OLLAMA_TIMEOUT   default: 120  (seconds)
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from gen_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.2:3b"
_DEFAULT_TIMEOUT = 120


class OllamaProvider(LLMProvider):
    """
    Calls Ollama /api/generate endpoint.
    Uses only stdlib (urllib) — no httpx/requests required.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")
        self._model = model or os.getenv("OLLAMA_MODEL") or _DEFAULT_MODEL
        self._timeout = int(timeout or os.getenv("OLLAMA_TIMEOUT") or _DEFAULT_TIMEOUT)
        logger.debug("OllamaProvider: %s model=%s", self._base_url, self._model)

    def complete(self, prompt: str) -> str:
        url = f"{self._base_url}/api/generate"
        payload = json.dumps(
            {"model": self._model, "prompt": prompt, "stream": False}
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return str(data.get("response", "")).strip()
        except urllib.error.URLError as exc:
            logger.warning("Ollama request failed: %s", exc)
            return f"[Ollama unavailable: {exc}]"
        except Exception as exc:
            logger.error("Ollama unexpected error: %s", exc)
            return "[Ollama error]"

    def is_available(self) -> bool:
        try:
            url = f"{self._base_url}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False
