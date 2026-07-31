"""Ferramentas de containers: container.build e container.run_sandbox (seção 15.1)."""
from typing import Any

from sandbox.runner.runner import run_in_sandbox


class ContainerBuild:
    name = "container.build"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        import docker

        client = docker.from_env()
        image, logs = client.images.build(
            path=arguments["workspace"],
            tag=arguments.get("tag", f"factory-build-{execution_id[:8]}"),
            rm=True,
        )
        return {"image": image.tags[0] if image.tags else image.id}


class ContainerRunSandbox:
    name = "container.run_sandbox"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await run_in_sandbox(
            workspace=arguments["workspace"],
            command=arguments["command"],
            timeout_seconds=int(arguments.get("timeout_seconds", 300)),
        )
