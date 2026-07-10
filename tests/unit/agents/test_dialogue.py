"""Unit tests for DialogueEngine."""
from gen_agent.dialogue.dialogue_engine import DialogueEngine


def test_stub_mode_produces_conversation():
    engine = DialogueEngine(llm=None, max_turns=4)
    conv = engine.run("a1", "Alice", "a2", "Bob", context="morning in the park")
    assert len(conv.utterances) == 4
    assert all(u.text for u in conv.utterances)


def test_custom_llm_is_called():
    call_log = []

    def fake_llm(prompt: str) -> str:
        call_log.append(prompt)
        # Generic response without names to avoid wrong-addressee detection
        return (
            "I was just thinking about what happened this morning at the cafe. "
            "The weather is quite lovely today, perfect for a walk in the town square."
        )

    engine = DialogueEngine(llm=fake_llm, max_turns=2, min_words=5, use_legacy_quality=False)
    conv = engine.run("a1", "Alice", "a2", "Bob")
    # At least 2 calls (one per turn minimum), at most max_attempts * max_turns
    assert len(call_log) >= 2
    assert len(conv.utterances) == 2


def test_transcript_format():
    engine = DialogueEngine(llm=None, max_turns=2)
    conv = engine.run("a1", "Alice", "a2", "Bob")
    transcript = conv.transcript()
    assert "Alice:" in transcript or "Bob:" in transcript


def test_participants_recorded():
    engine = DialogueEngine(llm=None, max_turns=2)
    conv = engine.run("a1", "Alice", "a2", "Bob")
    assert set(conv.participants) == {"a1", "a2"}


def test_deadline_returns_partial_conversation():
    import time

    engine = DialogueEngine(llm=None, max_turns=6, min_words=8)
    deadline = time.perf_counter() + 60.0
    conv = engine.run("a1", "Alice", "a2", "Bob", deadline=deadline)
    assert len(conv.utterances) >= 1
    assert len(conv.transcript().strip()) >= 10
