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
        return "Hello!"

    engine = DialogueEngine(llm=fake_llm, max_turns=2)
    conv = engine.run("a1", "Alice", "a2", "Bob")
    assert len(call_log) == 2
    assert all(u.text == "Hello!" for u in conv.utterances)


def test_transcript_format():
    engine = DialogueEngine(llm=None, max_turns=2)
    conv = engine.run("a1", "Alice", "a2", "Bob")
    transcript = conv.transcript()
    assert "Alice:" in transcript or "Bob:" in transcript


def test_participants_recorded():
    engine = DialogueEngine(llm=None, max_turns=2)
    conv = engine.run("a1", "Alice", "a2", "Bob")
    assert set(conv.participants) == {"a1", "a2"}
