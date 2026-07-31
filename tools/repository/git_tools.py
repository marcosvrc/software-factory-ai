"""Ferramentas de repositório Git: repository.read/diff/create_branch/commit (Épico 6)."""
from pathlib import Path
from typing import Any

from git import Repo


class RepositoryRead:
    name = "repository.read"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = Path(arguments["workspace"])
        rel_path = arguments.get("path", ".")
        target = (workspace / rel_path).resolve()
        if not str(target).startswith(str(workspace.resolve())):
            raise ValueError("path traversal bloqueado")
        if target.is_dir():
            files = [str(p.relative_to(workspace)) for p in target.rglob("*") if p.is_file()]
            return {"type": "directory", "files": files[:500]}
        return {"type": "file", "content": target.read_text(encoding="utf-8", errors="replace")[:100_000]}


class RepositoryDiff:
    name = "repository.diff"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        repo = Repo(arguments["workspace"])
        diff = repo.git.diff(arguments.get("base", "HEAD"))
        return {"diff": diff[:200_000]}


class RepositoryCreateBranch:
    name = "repository.create_branch"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        repo = Repo(arguments["workspace"])
        branch = repo.create_head(arguments["branch"])
        branch.checkout()
        return {"branch": branch.name}


class RepositoryCommit:
    name = "repository.commit"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        repo = Repo(arguments["workspace"])
        repo.git.add(A=True)
        commit = repo.index.commit(
            arguments.get("message", "commit automatizado pela fábrica"),
            author_date=None,
        )
        return {"commit": commit.hexsha}
