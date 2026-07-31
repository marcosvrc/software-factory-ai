"""Runner de sandbox efêmero (seção 16).

Princípio (16.1): código gerado nunca é executado diretamente no container do
orquestrador. Cada execução usa container efêmero com (16.2):
usuário não root, filesystem somente leitura exceto workspace, rede desabilitada,
CPU e memória limitadas, timeout, sem socket Docker, sem segredos, volume
dedicado e imagem previamente aprovada.

Proibições (16.4) são validadas por validate_sandbox_config antes de executar.
"""
import asyncio
import os
from typing import Any

from shared.exceptions import SandboxViolationError
from shared.logging import get_logger

logger = get_logger("sandbox.runner")

SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "factory-sandbox-python:latest")
ALLOWED_IMAGES = {
    image.strip()
    for image in os.getenv("SANDBOX_ALLOWED_IMAGES", SANDBOX_IMAGE).split(",")
}
CPU_LIMIT = float(os.getenv("SANDBOX_CPU_LIMIT", "1.0"))
MEMORY_LIMIT = os.getenv("SANDBOX_MEMORY_LIMIT", "1g")
DEFAULT_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "300"))

FORBIDDEN_MOUNTS = ("/", "/var/run/docker.sock")


def validate_sandbox_config(
    *, image: str, workspace: str, privileged: bool, user: str, network_mode: str
) -> None:
    """Aplica as proibições da seção 16.4."""
    if privileged:
        raise SandboxViolationError("--privileged é proibido")
    if workspace in FORBIDDEN_MOUNTS or workspace.rstrip("/") == "":
        raise SandboxViolationError(f"montagem proibida: {workspace}")
    if user in ("root", "0", "0:0"):
        raise SandboxViolationError("execução como root é proibida")
    if network_mode != "none":
        raise SandboxViolationError("acesso livre à rede é proibido no sandbox")
    if image not in ALLOWED_IMAGES:
        raise SandboxViolationError(f"imagem não aprovada: {image}")


async def run_in_sandbox(
    *,
    workspace: str,
    command: list[str],
    timeout_seconds: int = DEFAULT_TIMEOUT,
    image: str = SANDBOX_IMAGE,
) -> dict[str, Any]:
    """Fluxo (16.3): workspace isolado -> container efêmero -> execução ->
    coleta de evidências -> remoção do container."""
    user = "1000:1000"
    network_mode = "none"
    validate_sandbox_config(
        image=image, workspace=workspace, privileged=False, user=user, network_mode=network_mode
    )
    if timeout_seconds <= 0:
        raise SandboxViolationError("execução sem timeout é proibida")

    def _run() -> dict[str, Any]:
        import docker

        client = docker.from_env()
        container = client.containers.run(
            image=image,
            command=command,
            working_dir="/workspace",
            volumes={workspace: {"bind": "/workspace", "mode": "rw"}},
            user=user,
            network_mode=network_mode,
            read_only=True,
            tmpfs={"/tmp": "size=256m"},  # noqa: S108
            mem_limit=MEMORY_LIMIT,
            nano_cpus=int(CPU_LIMIT * 1e9),
            environment={},  # sem segredos
            detach=True,
            security_opt=["no-new-privileges"],
        )
        try:
            result = container.wait(timeout=timeout_seconds)
            logs = container.logs(stdout=True, stderr=True).decode(errors="replace")
            return {
                "exit_code": result.get("StatusCode", -1),
                "ok": result.get("StatusCode") == 0,
                "output": logs[-100_000:],
            }
        finally:
            container.remove(force=True)

    try:
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _run), timeout=timeout_seconds + 30
        )
    except asyncio.TimeoutError:
        return {"exit_code": -1, "ok": False, "output": "timeout do sandbox"}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"sandbox_unavailable error={str(exc)[:200]}")
        return {
            "exit_code": -1,
            "ok": False,
            "output": (
                "Sandbox indisponível (Docker não acessível a partir do worker). "
                "Veja sandbox/README.md para habilitar em desenvolvimento local. "
                f"Erro: {str(exc)[:300]}"
            ),
        }
