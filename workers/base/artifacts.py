"""Persistência de artefatos de resultado no MinIO com checksum (Épico 5)."""
import io
import json
import os

from shared.utils.checksum import sha256_bytes

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "factory")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "local-development-password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "factory")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


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
