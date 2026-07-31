import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Artifact, User
from app.schemas.api import ArtifactOut

router = APIRouter(tags=["artifacts"])


@router.get("/runs/{run_id}/artifacts", response_model=list[ArtifactOut])
async def run_artifacts(
    run_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Artifact]:
    result = await db.execute(
        select(Artifact).where(Artifact.workflow_run_id == run_id).order_by(Artifact.created_at)
    )
    return list(result.scalars())


@router.get("/artifacts/{artifact_id}", response_model=ArtifactOut)
async def get_artifact(
    artifact_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Artifact:
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(404, "Artefato não encontrado")
    return artifact


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> StreamingResponse:
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(404, "Artefato não encontrado")
    settings = get_settings()
    try:
        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        response = client.get_object(settings.minio_bucket, artifact.storage_key)
        data = response.read()
        response.close()
        response.release_conn()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Falha ao ler artefato no MinIO: {exc}") from exc
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{artifact.name}"'},
    )
