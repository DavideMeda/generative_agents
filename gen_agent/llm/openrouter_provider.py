"""
OpenRouter LLM provider — calls api.openrouter.ai via HTTP.

Environment variables:
    OPENROUTER_API_KEY   required
    OPENROUTER_MODEL     default: qwen/qwen3-235b-a22b:free
    OPENROUTER_TIMEOUT   default: 60
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from gen_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_MODEL = "qwen/qwen3-235b-a22b:free"
_DEFAULT_TIMEOUT = 60


class OpenRouterProvider(LLMProvider):
    """
    Calls OpenRouter /v1/chat/completions (OpenAI-compatible).
    Uses only stdlib — no openai SDK required.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self._model = model or os.getenv("OPENROUTER_MODEL", _DEFAULT_MODEL)
        self._timeout = int(timeout or os.getenv("OPENROUTER_TIMEOUT") or _DEFAULT_TIMEOUT)
        if not self._api_key:
            logger.warning("OpenRouterProvider: OPENROUTER_API_KEY not set")

    def complete(self, prompt: str) -> str:
        if not self._api_key:
            return "[OpenRouter: missing API key]"
        payload = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            _BASE_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "HTTP-Referer": "https://github.com/DavideMeda/generative_agents",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return str(data["choices"][0]["message"]["content"]).strip()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.warning("OpenRouter HTTP %s: %s", exc.code, body[:200])
            return f"[OpenRouter error {exc.code}]"
        except urllib.error.URLError as exc:
            logger.warning("OpenRouter request failed: %s", exc)
            return f"[OpenRouter unavailable: {exc}]"
        except Exception as exc:
            logger.error("OpenRouter unexpected error: %s", exc)
            return "[OpenRouter error]"

    def is_available(self) -> bool:
        return bool(self._api_key)
