"""Testes dos contratos (saída estruturada 11.3 e envelope 13.4)."""
import pytest
from pydantic import ValidationError

from shared.contracts.agent_result import AgentResult, Finding
from shared.contracts.message import MessageEnvelope


def test_agent_result_valid():
    result = AgentResult(
        agent_id="architecture.solution",
        execution_id="e-1",
        status="approved",
        summary="ok",
        findings=[
            Finding(
                id="f-1", severity="high", category="security",
                description="x", evidence=["a"], recommendation="fix",
            )
        ],
    )
    assert result.findings[0].severity == "high"


def test_agent_result_rejects_unknown_status():
    with pytest.raises(ValidationError):
        AgentResult(agent_id="a", execution_id="e", status="maybe", summary="")


def test_envelope_requires_correlation_id():
    with pytest.raises(ValidationError):
        MessageEnvelope()  # sem correlation_id


def test_envelope_defaults():
    envelope = MessageEnvelope(correlation_id="c-1")
    assert envelope.command == "execute_agent"
    assert envelope.attempt == 1
    assert envelope.message_id
