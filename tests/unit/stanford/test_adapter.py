"""
Tests per StanfordAdapter — M1 adapter hardening.

Copre:
  - stub mode (senza reverie)
  - protocol compliance (StanfordAdapterProtocol)
  - contract tests: mock LLM + register_persona + run_agent_plan
  - boundary rule: solo gen_agent/integrations/stanford/ può importare reverie
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

from gen_agent.integrations.stanford.adapter import StanfordAdapter, get_stanford_adapter
from gen_agent.interfaces.stanford_adapter_protocol import StanfordAdapterProtocol


class TestStubMode:
    def test_stub_mode_explicit(self):
        adapter = StanfordAdapter(stub_mode=True)
        assert adapter._stub is True

    def test_implements_protocol(self):
        adapter = StanfordAdapter(stub_mode=True)
        assert isinstance(adapter, StanfordAdapterProtocol)

    def test_register_persona_stores_name(self):
        adapter = StanfordAdapter(stub_mode=True)
        adapter.register_persona("a1", "Alice")
        assert adapter._persona_registry["a1"]["name"] == "Alice"

    def test_get_scratch_empty_on_fresh_agent(self):
        adapter = StanfordAdapter(stub_mode=True)
        assert adapter.get_agent_scratch("nonexistent") == {}

    def test_set_and_get_scratch_roundtrip(self):
        adapter = StanfordAdapter(stub_mode=True)
        adapter.register_persona("a1", "Alice")
        adapter.set_agent_scratch("a1", {"mood": "happy", "energy": 0.9})
        scratch = adapter.get_agent_scratch("a1")
        assert scratch["mood"] == "happy"
        assert scratch["energy"] == 0.9

    def test_set_scratch_updates_existing(self):
        adapter = StanfordAdapter(stub_mode=True)
        adapter.register_persona("a1", "Alice")
        adapter.set_agent_scratch("a1", {"mood": "happy"})
        adapter.set_agent_scratch("a1", {"mood": "tired"})
        assert adapter.get_agent_scratch("a1")["mood"] == "tired"

    def test_run_reflection_empty_returns_empty(self):
        adapter = StanfordAdapter(stub_mode=True)
        assert adapter.run_reflection("a1", []) == []

    def test_run_reflection_no_llm_returns_summary(self):
        adapter = StanfordAdapter(stub_mode=True, llm=None)
        result = adapter.run_reflection("a1", ["mem1", "mem2", "mem3"])
        assert isinstance(result, list)
        assert len(result) == 1
        assert "3" in result[0]

    def test_get_persona_returns_none_when_not_registered(self):
        adapter = StanfordAdapter(stub_mode=True)
        assert adapter._get_persona("missing") is None

    def test_set_scratch_auto_registers_unknown_agent(self):
        adapter = StanfordAdapter(stub_mode=True)
        adapter.set_agent_scratch("new_agent", {"key": "val"})
        assert adapter.get_agent_scratch("new_agent")["key"] == "val"


class TestContractWithMockLLM:
    """Contract tests: adapter con mock LLM (nessuna connessione Ollama/OpenAI)."""

    def _adapter(self, llm_response: str = '{"plan": ["go to the Cafe"], "focus": "social"}'):
        llm = MagicMock(return_value=llm_response)
        a = StanfordAdapter(stub_mode=True, llm=llm)
        a.register_persona("a1", "Alice")
        return a, llm

    def test_run_agent_plan_returns_required_keys(self):
        adapter, _ = self._adapter()
        result = adapter.run_agent_plan("a1", {"tick": 1, "location": "park"})
        assert "plan" in result
        assert "action" in result
        assert "plan_text" in result

    def test_run_agent_plan_invokes_llm_exactly_once(self):
        adapter, llm = self._adapter()
        adapter.run_agent_plan("a1", {"tick": 1})
        llm.assert_called_once()

    def test_run_agent_plan_passes_poi_names_to_prompt(self):
        adapter, llm = self._adapter('{"plan": ["visit the Library"], "focus": "learn"}')
        adapter.run_agent_plan(
            "a1",
            {"tick": 2, "location": "downtown", "poi_names": ["Library", "Park", "Cafe"]},
        )
        prompt = llm.call_args[0][0]
        assert "Library" in prompt

    def test_run_agent_plan_unregistered_agent_does_not_crash(self):
        adapter, _ = self._adapter()
        result = adapter.run_agent_plan("unknown_id", {"tick": 0})
        assert isinstance(result, dict)

    def test_run_reflection_with_llm_returns_list(self):
        llm = MagicMock(return_value="Alice reflected on the day.")
        adapter = StanfordAdapter(stub_mode=True, llm=llm)
        result = adapter.run_reflection("a1", ["went to cafe", "met Bob"])
        assert isinstance(result, list)
        assert len(result) > 0

    def test_run_reflection_llm_exception_returns_empty(self):
        llm = MagicMock(side_effect=RuntimeError("LLM unavailable"))
        adapter = StanfordAdapter(stub_mode=True, llm=llm)
        result = adapter.run_reflection("a1", ["memory"])
        assert result == []

    def test_run_agent_plan_with_memories_context(self):
        adapter, llm = self._adapter()
        adapter.run_agent_plan(
            "a1",
            {"tick": 5, "memories": ["visited park yesterday", "talked to Bob"]},
        )
        prompt = llm.call_args[0][0]
        assert "park" in prompt.lower() or "Bob" in prompt


class TestFactoryFunction:
    def test_get_stanford_adapter_returns_instance(self):
        adapter = get_stanford_adapter()
        assert isinstance(adapter, StanfordAdapter)

    def test_get_stanford_adapter_with_llm_wired(self):
        llm = MagicMock(return_value='{"plan": [], "focus": "idle"}')
        adapter = get_stanford_adapter(llm=llm)
        assert adapter._llm is llm


class TestBoundaryImportRule:
    """
    Regola architetturale: solo gen_agent/integrations/stanford/ può importare reverie.
    Scansione AST dei soli top-level package del progetto
    (gen_agent, server, config, scenarios, scripts, benchmarks).
    """

    # Scansiona solo questi package top-level — esclude reverie/, environment/, portfolio/
    _SCAN_DIRS = ("gen_agent", "server", "config", "scenarios", "scripts", "benchmarks")

    def test_no_reverie_import_outside_stanford_integration(self):
        project_root = Path(__file__).resolve().parents[4]
        allowed_dir = project_root / "gen_agent" / "integrations" / "stanford"
        violations: List[str] = []

        for top in self._SCAN_DIRS:
            top_dir = project_root / top
            if not top_dir.exists():
                continue
            for py_file in top_dir.rglob("*.py"):
                # file dentro la directory permessa → skip
                try:
                    py_file.relative_to(allowed_dir)
                    continue
                except ValueError:
                    pass
                try:
                    source = py_file.read_text(encoding="utf-8", errors="ignore")
                    tree = ast.parse(source)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name == "reverie" or alias.name.startswith("reverie."):
                                violations.append(str(py_file.relative_to(project_root)))
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        if mod == "reverie" or mod.startswith("reverie."):
                            violations.append(str(py_file.relative_to(project_root)))

        assert violations == [], (
            "Boundary violation: i seguenti file importano reverie fuori da "
            f"gen_agent/integrations/stanford/:\n" + "\n".join(violations)
        )
