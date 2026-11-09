from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "agent-demo" / "fabric_agent_client.py"
SPEC = importlib.util.spec_from_file_location("fabric_agent_client", MODULE_PATH)
assert SPEC and SPEC.loader
CLIENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLIENT)


def test_validate_question_normalizes_whitespace() -> None:
    assert CLIENT.validate_question("  show   ORDER000123\nstatus ") == "show ORDER000123 status"


@pytest.mark.parametrize("value", ["", "   "])
def test_validate_question_rejects_empty_values(value: object) -> None:
    with pytest.raises(ValueError):
        CLIENT.validate_question(value)


@pytest.mark.parametrize("value", [None, 123])
def test_validate_question_rejects_non_strings(value: object) -> None:
    with pytest.raises(TypeError):
        CLIENT.validate_question(value)


def test_validate_question_rejects_oversize() -> None:
    with pytest.raises(ValueError, match="500"):
        CLIENT.validate_question("x" * 501)


def test_resolve_agent_id_is_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FABRIC_ONTOLOGY_AGENT_ID", "ontology-id")
    monkeypatch.setenv("FABRIC_DIRECT_AGENT_ID", "direct-id")
    monkeypatch.setenv("FABRIC_SEMANTIC_AGENT_ID", "semantic-id")
    monkeypatch.setenv("FABRIC_HYBRID_AGENT_ID", "hybrid-id")
    assert CLIENT.resolve_agent_id("ontology") == ("ontology", "ontology-id")
    assert CLIENT.resolve_agent_id("direct") == ("direct", "direct-id")
    assert CLIENT.resolve_agent_id("semantic") == ("semantic", "semantic-id")
    assert CLIENT.resolve_agent_id("hybrid") == ("hybrid", "hybrid-id")
    assert CLIENT.resolve_agent_id(None) == ("direct", "direct-id")
    with pytest.raises(ValueError, match="hybrid"):
        CLIENT.resolve_agent_id("another-agent")
