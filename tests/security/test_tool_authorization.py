"""Menor privilégio (3.6/15.3): ferramenta fora da allowlist é bloqueada."""
import pytest

from shared.exceptions import ToolNotAllowedError
from tools.base import authorized_call


DEFINITION = {
    "id": "product.product-owner",
    "tools": {"allowed": ["artifact.read"], "denied": ["shell.unrestricted"]},
}


async def test_denied_tool_blocked():
    with pytest.raises(ToolNotAllowedError):
        await authorized_call(
            tool_name="shell.unrestricted",
            agent_definition=DEFINITION,
            execution_id="e-1",
            arguments={},
        )


async def test_tool_not_in_allowlist_blocked():
    with pytest.raises(ToolNotAllowedError):
        await authorized_call(
            tool_name="repository.commit",
            agent_definition=DEFINITION,
            execution_id="e-1",
            arguments={},
        )
