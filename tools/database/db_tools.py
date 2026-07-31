"""Ferramentas de banco: database.inspect_schema e database.validate_migration."""
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


class DatabaseInspectSchema:
    name = "database.inspect_schema"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        engine = create_async_engine(arguments["database_url"], pool_pre_ping=True)
        async with engine.connect() as conn:
            def _inspect(sync_conn):
                inspector = inspect(sync_conn)
                return {
                    table: [c["name"] for c in inspector.get_columns(table)]
                    for table in inspector.get_table_names()
                }

            schema = await conn.run_sync(_inspect)
        await engine.dispose()
        return {"schema": schema}


class DatabaseValidateMigration:
    name = "database.validate_migration"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Valida sintaticamente uma migração SQL em transação com rollback."""
        engine = create_async_engine(arguments["database_url"], pool_pre_ping=True)
        sql = arguments["sql"]
        destructive = any(
            keyword in sql.upper() for keyword in ("DROP TABLE", "DROP COLUMN", "TRUNCATE")
        )
        if destructive and not arguments.get("approved_by_human"):
            await engine.dispose()
            return {
                "valid": False,
                "reason": "mudança destrutiva exige aprovação humana (seção 17.1)",
            }
        try:
            async with engine.connect() as conn:
                trans = await conn.begin()
                await conn.execute(text(sql))
                await trans.rollback()
            return {"valid": True}
        except Exception as exc:  # noqa: BLE001
            return {"valid": False, "reason": str(exc)[:1000]}
        finally:
            await engine.dispose()
