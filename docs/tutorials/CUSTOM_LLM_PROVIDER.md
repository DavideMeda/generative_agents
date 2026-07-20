# Integrating a New LLM Provider

This tutorial shows how to add a custom LLM provider to New Gen Agent.

**Example:** We'll integrate **Anthropic Claude** via their official Python SDK.

---

## Step 1: Define the provider class

Create `gen_agent/llm/anthropic_provider.py`:

```python
"""AnthropicProvider — Claude 3 Opus/Sonnet/Haiku via official SDK."""
from __future__ import annotations

import logging
import os

from gen_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude provider using the official `anthropic` Python SDK.
    
    Requires:
        pip install anthropic
        export ANTHROPIC_API_KEY=sk-ant-...
    
    Models:
        - claude-3-opus-20240229 (best quality, slower, $15/$75 per 1M tokens)
        - claude-3-5-sonnet-20241022 (balanced, $3/$15 per 1M tokens)
        - claude-3-haiku-20240307 (fastest, cheapest, $0.25/$1.25 per 1M tokens)
    """

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client = None
        self._api_key = os.getenv("ANTHROPIC_API_KEY", "")

    def _ensure_client(self) -> None:
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError:
                logger.error("anthropic package not installed. Run: pip install anthropic")
                raise

    def complete(self, prompt: str) -> str:
        """
        Send a prompt to Claude and return the response text.
        
        Maps our generic prompt to Anthropic's Messages API format.
        """
        if not self._api_key:
            return "[AnthropicProvider: ANTHROPIC_API_KEY not set]"

        self._ensure_client()

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            # Extract text from first content block
            if response.content and len(response.content) > 0:
                return response.content[0].text
            return "[AnthropicProvider: empty response]"

        except Exception as exc:
            logger.warning("Anthropic API call failed: %s", exc)
            return f"[AnthropicProvider error: {exc}]"

    def is_available(self) -> bool:
        """Check if the provider is ready (API key set, package installed)."""
        if not self._api_key:
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False
```

---

## Step 2: Register the provider in `engine_factory.py`

Edit `config/engine_factory.py`:

### 2.1 Add provider option

In `_build_llm_provider()`:

```python
def _build_llm_provider(scenario: Any) -> Any:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    
    if provider == "anthropic":
        from gen_agent.llm.anthropic_provider import AnthropicProvider
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        llm_prov = AnthropicProvider(model=model, max_tokens=512, temperature=0.7)
        if not llm_prov.is_available():
            warnings.warn("Anthropic provider unavailable (missing key or SDK), falling back to mock")
            from gen_agent.llm.mock_provider import MockProvider
            llm_prov = MockProvider()
    elif provider == "ollama":
        ...
    # ... other providers
```

---

## Step 3: Add circuit breaker bypass (optional)

If you want to skip the circuit breaker for cloud APIs (they have their own rate limits):

In `_build_llm_provider()`, after instantiating `AnthropicProvider`:

```python
if provider == "anthropic":
    ...
    # No circuit breaker for cloud APIs (they handle rate limits internally)
    return llm_prov
```

Otherwise, wrap it:

```python
if provider == "anthropic":
    ...
    from gen_agent.llm.circuit_breaker import CircuitBreaker
    return CircuitBreaker(llm_prov, failure_threshold=3, recovery_timeout=30.0)
```

---

## Step 4: Document usage

Add to `README.md` and `docs/tutorials/GETTING_STARTED.md`:

```markdown
### With Anthropic Claude

```bash
# 1. Install SDK
pip install anthropic

# 2. Get API key from https://console.anthropic.com
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Run simulation
export LLM_PROVIDER=anthropic
export ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
python examples/ollama_simple.py  # or any other script
```

**Models:**
- `claude-3-opus-20240229` — Best quality (slower, more expensive)
- `claude-3-5-sonnet-20241022` — Balanced (recommended)
- `claude-3-haiku-20240307` — Fastest, cheapest
```

---

## Step 5: Test the provider

Create `tests/unit/llm/test_anthropic_provider.py`:

```python
"""Unit tests for AnthropicProvider."""
import os
from unittest.mock import MagicMock, patch

import pytest

from gen_agent.llm.anthropic_provider import AnthropicProvider


def test_is_available_when_key_set():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        with patch("gen_agent.llm.anthropic_provider.anthropic"):
            provider = AnthropicProvider()
            assert provider.is_available() is True


def test_is_available_when_key_missing():
    with patch.dict(os.environ, {}, clear=True):
        provider = AnthropicProvider()
        assert provider.is_available() is False


def test_complete_returns_error_when_key_missing():
    with patch.dict(os.environ, {}, clear=True):
        provider = AnthropicProvider()
        result = provider.complete("Hello")
        assert "ANTHROPIC_API_KEY not set" in result


@patch("gen_agent.llm.anthropic_provider.anthropic")
def test_complete_returns_text_from_api(mock_anthropic):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Hello from Claude")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.Anthropic.return_value = mock_client

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        provider = AnthropicProvider(model="claude-3-haiku-20240307")
        result = provider.complete("Say hello")
        
        assert result == "Hello from Claude"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-haiku-20240307"
        assert call_kwargs["messages"][0]["content"] == "Say hello"


@patch("gen_agent.llm.anthropic_provider.anthropic")
def test_complete_handles_api_error(mock_anthropic):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API timeout")
    mock_anthropic.Anthropic.return_value = mock_client

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        provider = AnthropicProvider()
        result = provider.complete("Test")
        
        assert "error" in result.lower()
        assert "API timeout" in result
```

Run tests:

```bash
pytest tests/unit/llm/test_anthropic_provider.py -v
```

---

## Step 6: Add to example scripts

Create `examples/anthropic_simple.py`:

```python
#!/usr/bin/env python3
"""Example: Using Anthropic Claude for agent dialogues."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gen_agent.llm.anthropic_provider import AnthropicProvider  # noqa: E402
from gen_agent.dialogue.dialogue_engine import DialogueEngine  # noqa: E402
from gen_agent.memory.manager import MemoryManager  # noqa: E402
from gen_agent.sim.engine import SimConfig, SimEngine  # noqa: E402
from gen_agent.interfaces.sim_protocol import AgentConfig  # noqa: E402

AGENTS = ["Alice", "Bob"]
TICKS = 20


def main() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set, using mock LLM instead.")
        print("   To use Claude: export ANTHROPIC_API_KEY=sk-ant-...")
        llm_provider = None
    else:
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        print(f"✓ Using Anthropic Claude ({model})")
        llm_provider = AnthropicProvider(model=model, max_tokens=512, temperature=0.7)
        if not llm_provider.is_available():
            print("⚠️  anthropic package not installed. Run: pip install anthropic")
            llm_provider = None

    memory = MemoryManager()
    dialogue = DialogueEngine(
        llm=llm_provider.complete if llm_provider else None,
        memory_store=memory,
        max_turns=4,
    )

    cfg = SimConfig(
        tick_interval_sec=0.0,
        interaction_radius=5.0,
        block_on_dialogue=True,
        dialogue_max_turns=4,
        seed=42,
    )
    engine = SimEngine(config=cfg, dialogue_engine=dialogue, memory_store=memory)

    for idx, name in enumerate(AGENTS):
        engine.register_agent(AgentConfig(
            agent_id=f"a{idx+1}",
            name=name,
            position=(idx * 2.0, 0.0)
        ))

    print(f"\n=== Simulation: {len(AGENTS)} agents, {TICKS} ticks ===\n")

    for tick_num in range(1, TICKS + 1):
        result = engine.advance()
        for event in result.events:
            if event.get("type") == "interaction":
                agents_str = " & ".join(event.get("agent_names", []))
                print(f"  tick {tick_num:2d}  {agents_str}")

    stats = engine.stats()
    print(f"\n--- Final stats ---")
    print(f"  Interactions: {stats['interactions']}")
    print(f"  Dialogues: {stats['dialogues']}")
    print(f"  Memories: {memory.count()}")
    print("\nDone.")


if __name__ == "__main__":
    main()
```

---

## Best practices

1. **API key handling:** Always check for API key in `is_available()` and `complete()`
2. **Error handling:** Catch API exceptions and return error strings (not raise)
3. **Lazy init:** Initialize SDK client only when first needed (faster startup)
4. **Token limits:** Respect model token limits (set `max_tokens` appropriately)
5. **Rate limiting:** Use circuit breaker or provider's built-in backoff
6. **Testing:** Mock the SDK in unit tests (avoid real API calls in CI)
7. **Documentation:** Document model names, pricing, and API key setup

---

## Troubleshooting

**Problem:** `ImportError: No module named 'anthropic'`  
**Solution:** `pip install anthropic`

**Problem:** `ANTHROPIC_API_KEY not set`  
**Solution:** Get key from https://console.anthropic.com and `export ANTHROPIC_API_KEY=sk-ant-...`

**Problem:** `rate_limit_error` or `overloaded_error`  
**Solution:** Add exponential backoff in `complete()` or reduce request frequency

**Problem:** Empty responses  
**Solution:** Check model name, increase `max_tokens`, verify prompt format

---

## Next steps

- Add support for **system prompts** (Anthropic's `system` parameter)
- Implement **streaming** for long responses (use `stream=True` in Messages API)
- Add **cost tracking** (log input/output tokens, calculate spend)
- Compare **Claude vs GPT vs Ollama** dialogue quality for your use case

See also:
- Anthropic API docs: https://docs.anthropic.com/
- `gen_agent/llm/ollama_provider.py` — reference local provider
- `gen_agent/llm/openrouter_provider.py` — reference cloud provider
