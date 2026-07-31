"""Ferramentas de código: code.search/patch/format (Épico 6)."""
import asyncio
import subprocess
from pathlib import Path
from typing import Any


class CodeSearch:
    name = "code.search"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = Path(arguments["workspace"]).resolve()
        pattern = arguments["pattern"]
        matches: list[dict] = []
        for path in workspace.rglob("*.py"):
            try:
                for lineno, line in enumerate(
                    path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                ):
                    if pattern in line:
                        matches.append(
                            {"file": str(path.relative_to(workspace)), "line": lineno,
                             "text": line.strip()[:200]}
                        )
                        if len(matches) >= 200:
                            return {"matches": matches, "truncated": True}
            except OSError:
                continue
        return {"matches": matches, "truncated": False}


class CodePatch:
    name = "code.patch"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Aplica um patch unificado dentro do workspace via `git apply`."""
        workspace = Path(arguments["workspace"]).resolve()
        patch = arguments["patch"]
        proc = await asyncio.create_subprocess_exec(
            "git", "apply", "--whitespace=nowarn", "-",
            cwd=workspace, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(patch.encode())
        return {
            "applied": proc.returncode == 0,
            "stderr": stderr.decode(errors="replace")[:5000],
        }


class CodeFormat:
    name = "code.format"

    async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = Path(arguments["workspace"]).resolve()
        proc = await asyncio.create_subprocess_exec(
            "ruff", "format", ".", cwd=workspace,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {"ok": proc.returncode == 0, "output": stdout.decode(errors="replace")[:5000]}
