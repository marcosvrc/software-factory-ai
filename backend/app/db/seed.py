"""Seed de desenvolvimento: usuários locais com papéis da seção 20.2.

Senhas apenas para ambiente local. Troque imediatamente em qualquer outro uso.
"""
import asyncio

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.models import User

USERS = [
    ("admin", "admin", "ADMIN"),
    ("manager", "manager", "FACTORY_MANAGER"),
    ("approver", "approver", "APPROVER"),
    ("developer", "developer", "DEVELOPER"),
    ("auditor", "auditor", "AUDITOR"),
    ("viewer", "viewer", "VIEWER"),
]


async def seed() -> None:
    async with SessionLocal() as db:
        for username, password, role in USERS:
            existing = (
                await db.execute(select(User).where(User.username == username))
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    User(
                        username=username,
                        email=f"{username}@factory.local",
                        password_hash=hash_password(password),
                        role=role,
                    )
                )
                print(f"usuário criado: {username} ({role})")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
