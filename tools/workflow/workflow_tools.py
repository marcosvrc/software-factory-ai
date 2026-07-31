"""Ferramentas de workflow: request_approval, report_finding, complete_task,
documentation.generate, diagram.generate e standards.search (seção 15.1)."""
from typing import Any

from workers.base import persistence


class WorkflowRequestApproval:
    name = "workflow.request_approval"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        approvals = await persistence.table("approvals")
        from sqlalchemy import insert

        approval_id = persistence.new_id()
        async with persistence.engine.begin() as conn:
            await conn.execute(
                insert(approvals).values(
                    id=approval_id,
                    workflow_run_id=arguments["workflow_run_id"],
                    task_id=arguments.get("task_id"),
                    approval_type=arguments.get("approval_type", "generic"),
                    status="REQUESTED",
                    requested_from=arguments.get("requested_from", "APPROVER"),
                    summary=arguments.get("summary", ""),
                    impacts=arguments.get("impacts", []),
                    risks=arguments.get("risks", []),
                    alternatives=arguments.get("alternatives", []),
                    recommendation=arguments.get("recommendation"),
                    artifacts=arguments.get("artifacts", []),
                    requested_at=persistence.now(),
                    created_at=persistence.now(),
                    updated_at=persistence.now(),
                )
            )
        return {"approval_id": approval_id, "status": "REQUESTED"}


class WorkflowReportFinding:
    name = "workflow.report_finding"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        await persistence.record_findings(
            arguments["task_id"], execution_id, [arguments["finding"]]
        )
        return {"recorded": True}


class WorkflowCompleteTask:
    name = "workflow.complete_task"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        await persistence.update_task_status(arguments["task_id"], "DONE")
        return {"status": "DONE"}


class DocumentationGenerate:
    name = "documentation.generate"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Persiste documentação markdown como artefato."""
        from tools.artifacts.minio_tools import ArtifactWrite

        return await ArtifactWrite().execute(
            execution_id=execution_id,
            arguments={"key": arguments["key"], "content": arguments["content"]},
        )


class DiagramGenerate:
    name = "diagram.generate"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Persiste diagramas Mermaid (.mmd) como artefato."""
        from tools.artifacts.minio_tools import ArtifactWrite

        return await ArtifactWrite().execute(
            execution_id=execution_id,
            arguments={"key": arguments["key"], "content": arguments["mermaid"]},
        )


class StandardsSearch:
    name = "standards.search"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Busca padrões no catálogo local (docs/architecture)."""
        from pathlib import Path

        catalog = Path(arguments.get("catalog_path", "/app/docs/architecture"))
        query = arguments.get("query", "").lower()
        hits = []
        if catalog.exists():
            for path in catalog.rglob("*.md"):
                text = path.read_text(encoding="utf-8", errors="replace")
                if query in text.lower():
                    hits.append({"file": str(path), "excerpt": text[:500]})
        return {"hits": hits[:20]}
