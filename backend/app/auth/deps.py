"""Dependências de autenticação e autorização (papéis da seção 20.2)."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_token
from app.db.session import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = {
    "ADMIN": 60,
    "FACTORY_MANAGER": 50,
    "APPROVER": 40,
    "DEVELOPER": 30,
    "AUDITOR": 20,
    "VIEWER": 10,
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")
    try:
        payload = decode_token(credentials.credentials)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from exc
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tipo de token inválido")
    user = (
        await db.execute(select(User).where(User.username == payload["sub"]))
    ).scalar_one_or_none()
    if user is None or not user.enabled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inválido")
    return user


def require_role(minimum: str):
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_HIERARCHY.get(user.role, 0) < ROLE_HIERARCHY[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requer papel {minimum} ou superior")
        return user

    return _dep
