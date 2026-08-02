"""Persistência de artefatos de resultado no MinIO com checksum (Épico 5)."""
import io
import json
import os
from pathlib import Path

from shared.exceptions import SandboxViolationError
from shared.logging import get_logger
from shared.utils.checksum import sha256_bytes

logger = get_logger("workers.artifacts")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "factory")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "local-development-password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "factory")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))


def _client():
    from minio import Minio

    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


async def store_result_artifact(
    *, workflow_run_id: str, task_id: str, agent_id: str, payload: dict
) -> str | None:
    """Grava o AgentResult como artefato JSON. Retorna a referência minio://..."""
    data = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode()
    key = f"runs/{workflow_run_id}/tasks/{task_id}/{agent_id.replace('.', '-')}-result.json"
    try:
        client = _client()
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
        client.put_object(
            MINIO_BUCKET, key, io.BytesIO(data), length=len(data),
            content_type="application/json",
            metadata={"checksum": sha256_bytes(data)},
        )
        return f"minio://{MINIO_BUCKET}/{key}"
    except Exception:  # noqa: BLE001
        return None


async def store_code_file(
    *, workflow_run_id: str, task_id: str, path: str, content: str
) -> tuple[str, str] | None:
    """Grava o conteúdo real de um arquivo de código no MinIO.

    Retorna (reference, checksum) ou None em caso de falha. Diferente de
    store_result_artifact: guarda o CONTEÚDO do arquivo (não o JSON do
    AgentResult), para que possa ser lido de volta como contexto real por
    agentes subsequentes e listado como artefato de primeira classe.
    """
    data = content.encode()
    safe_path = path.lstrip("/")
    key = f"runs/{workflow_run_id}/tasks/{task_id}/code/{safe_path}"
    try:
        client = _client()
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
        checksum = sha256_bytes(data)
        client.put_object(
            MINIO_BUCKET, key, io.BytesIO(data), length=len(data),
            content_type="text/plain",
            metadata={"checksum": checksum},
        )
        return f"minio://{MINIO_BUCKET}/{key}", checksum
    except Exception:  # noqa: BLE001
        return None


def write_code_file_to_workspace(*, project_id: str, path: str, content: str) -> str | None:
    """Materializa o arquivo de código em disco, em WORKSPACES_ROOT/<project_id>/<path>.

    Isso permite abrir o projeto gerado num editor normal, além da cópia já
    persistida no MinIO (fonte de verdade para auditoria/versionamento).
    `path` vem do modelo de IA e NÃO é confiável: validamos que o destino
    final continua dentro do workspace do projeto (bloqueio de path
    traversal via "../" ou paths absolutos).
    """
    if not project_id:
        return None
    workspace = (WORKSPACES_ROOT / project_id).resolve()
    target = (workspace / path.lstrip("/")).resolve()
    try:
        target.relative_to(workspace)
    except ValueError:
        logger.warning(f"path_traversal_blocked project_id={project_id} path={path}")
        raise SandboxViolationError(f"path fora do workspace do projeto: {path}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)
    except OSError:
        logger.exception(f"workspace_write_failed project_id={project_id} path={path}")
        return None
