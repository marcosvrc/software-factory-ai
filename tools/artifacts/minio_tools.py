"""Ferramentas de artefatos: artifact.read/write/list com checksum e versão (Épico 5)."""
import io
import json
import os
from typing import Any

from shared.utils.checksum import sha256_bytes

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "factory")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "local-development-password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "factory")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


def _client():
    from minio import Minio

    return Minio(
        MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE,
    )


class ArtifactWrite:
    name = "artifact.write"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        key = arguments["key"]
        content = arguments["content"]
        data = (
            content.encode() if isinstance(content, str) else json.dumps(content).encode()
        )
        client = _client()
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
        checksum = sha256_bytes(data)
        client.put_object(
            MINIO_BUCKET, key, io.BytesIO(data), length=len(data),
            metadata={"checksum": checksum, "execution_id": execution_id},
        )
        return {"reference": f"minio://{MINIO_BUCKET}/{key}", "checksum": checksum}


class ArtifactRead:
    name = "artifact.read"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        key = arguments["key"].replace(f"minio://{MINIO_BUCKET}/", "")
        response = _client().get_object(MINIO_BUCKET, key)
        data = response.read()
        response.close()
        response.release_conn()
        return {"content": data.decode(errors="replace")[:200_000]}


class ArtifactList:
    name = "artifact.list"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        prefix = arguments.get("prefix", "")
        objects = _client().list_objects(MINIO_BUCKET, prefix=prefix, recursive=True)
        return {"keys": [o.object_name for o in objects][:1000]}
