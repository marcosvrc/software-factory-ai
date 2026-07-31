from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models import User
from app.schemas.api import LoginRequest, RefreshRequest, TokenResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = (
        await db.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()
    if user is None or not user.enabled or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    refresh = create_refresh_token(user.username, user.role)
    user.refresh_token_hash = hash_password(refresh)
    await record_audit(
        db, event_type="login", actor_type="human", actor_id=user.username,
        entity_type="user", entity_id=user.id,
    )
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(user.username, user.role), refresh_token=refresh
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token inválido") from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tipo de token inválido")
    user = (
        await db.execute(select(User).where(User.username == payload["sub"]))
    ).scalar_one_or_none()
    if user is None or not user.enabled or not user.refresh_token_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revogado")
    if not verify_password(body.refresh_token, user.refresh_token_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token rotacionado")
    new_refresh = create_refresh_token(user.username, user.role)
    user.refresh_token_hash = hash_password(new_refresh)  # rotação
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(user.username, user.role), refresh_token=new_refresh
    )
