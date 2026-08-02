"""API de configuração de servidores MCP (Model Context Protocol).

Fase 1: cadastro, teste de conexão e descoberta de ferramentas. Os agentes
declaram quais servidores podem usar em
`agent_definitions.configuration["mcp_servers"]`; a execução das ferramentas
pelos agentes é a fase 2.

Segurança: um servidor com transporte "stdio" é um comando arbitrário executado
dentro do container da API. Criar/editar/testar exige papel ADMIN (acima do
usado no restante da configuração) e servidores nascem desabilitados. Valores de
`env`/`headers` podem conter credenciais e nunca são devolvidos pela API.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models import AgentDefinition, McpServer, User
from app.schemas.api import (
    McpOAuthStartOut,
    McpServerCreate,
    McpServerOut,
    McpServerUpdate,
)
from app.services import mcp_oauth
from app.services.audit import record_audit
from shared.mcp import (
    MCPAuthorizationRequired,
    MCPConnectionError,
    MCPOAuthError,
    MCPServerConfig,
    discover_tools,
)

router = APIRouter(prefix="/mcp/servers", tags=["mcp"])

MAX_ERROR_CHARS = 2000


def _to_out(server: McpServer, used_by: list[str] | None = None) -> McpServerOut:
    return McpServerOut(
        id=server.id,
        name=server.name,
        description=server.description,
        transport=server.transport,
        command=server.command,
        args=server.args or [],
        url=server.url,
        timeout_seconds=server.timeout_seconds,
        enabled=server.enabled,
        tools=server.tools or [],
        last_status=server.last_status,
        last_error=server.last_error,
        last_checked_at=server.last_checked_at,
        created_at=server.created_at,
        updated_at=server.updated_at,
        env_keys=sorted((server.env or {}).keys()),
        header_keys=sorted((server.headers or {}).keys()),
        used_by_agents=used_by or [],
        # Somente o estado da autorização: tokens e client_secret nunca saem.
        auth_status=mcp_oauth.authorization_status(server),
        oauth_expires_at=server.oauth_expires_at,
        oauth_scope=server.oauth_scope,
        has_oauth_client=bool(server.oauth_client_id),
    )


def _to_config(server: McpServer, access_token: str | None = None) -> MCPServerConfig:
    return MCPServerConfig(
        name=server.name,
        transport=server.transport,
        command=server.command,
        args=server.args or [],
        env=server.env or {},
        url=server.url,
        headers=server.headers or {},
        timeout_seconds=float(server.timeout_seconds),
        access_token=access_token,
    )


async def _agents_using(db: AsyncSession, server_name: str) -> list[str]:
    """Agentes cuja configuração declara este servidor MCP."""
    agents = (await db.execute(select(AgentDefinition))).scalars()
    return sorted(
        agent.id
        for agent in agents
        if server_name in ((agent.configuration or {}).get("mcp_servers") or [])
    )


def _validate_transport_fields(transport: str, command: str | None, url: str | None) -> None:
    if transport == "stdio" and not (command or "").strip():
        raise HTTPException(422, "Transporte stdio exige 'command'")
    if transport == "http" and not (url or "").strip():
        raise HTTPException(422, "Transporte http exige 'url'")


@router.get("", response_model=list[McpServerOut])
async def list_servers(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[McpServerOut]:
    servers = list((await db.execute(select(McpServer).order_by(McpServer.name))).scalars())
    agents = list((await db.execute(select(AgentDefinition))).scalars())
    usage: dict[str, list[str]] = {}
    for agent in agents:
        for name in (agent.configuration or {}).get("mcp_servers") or []:
            usage.setdefault(name, []).append(agent.id)
    return [_to_out(s, sorted(usage.get(s.name, []))) for s in servers]


@router.post("", response_model=McpServerOut, status_code=201)
async def create_server(
    body: McpServerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("ADMIN")),
) -> McpServerOut:
    _validate_transport_fields(body.transport, body.command, body.url)
    exists = (
        await db.execute(select(McpServer).where(McpServer.name == body.name))
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(409, f"Já existe um servidor MCP chamado '{body.name}'")
    server = McpServer(
        name=body.name,
        description=body.description,
        transport=body.transport,
        command=body.command,
        args=body.args,
        env=body.env,
        url=body.url,
        headers=body.headers,
        timeout_seconds=body.timeout_seconds,
        enabled=body.enabled,
        tools=[],
    )
    db.add(server)
    await db.flush()
    await record_audit(
        db,
        event_type="config.changed",
        actor_type="human",
        actor_id=user.username,
        entity_type="mcp_server",
        entity_id=server.id,
        after_state={"name": server.name, "transport": server.transport, "created": True},
    )
    await db.commit()
    await db.refresh(server)
    return _to_out(server)


@router.get("/{server_id}", response_model=McpServerOut)
async def get_server(
    server_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> McpServerOut:
    server = await db.get(McpServer, server_id)
    if server is None:
        raise HTTPException(404, "Servidor MCP não encontrado")
    return _to_out(server, await _agents_using(db, server.name))


@router.patch("/{server_id}", response_model=McpServerOut)
async def update_server(
    server_id: str,
    body: McpServerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("ADMIN")),
) -> McpServerOut:
    server = await db.get(McpServer, server_id)
    if server is None:
        raise HTTPException(404, "Servidor MCP não encontrado")
    before = {"enabled": server.enabled, "transport": server.transport}

    for field in ("description", "command", "url", "args", "headers", "timeout_seconds"):
        value = getattr(body, field)
        if value is not None:
            setattr(server, field, value)
    if body.transport is not None:
        server.transport = body.transport
    if body.env is not None:
        server.env = body.env
    if body.enabled is not None:
        server.enabled = body.enabled

    _validate_transport_fields(server.transport, server.command, server.url)

    await record_audit(
        db,
        event_type="config.changed",
        actor_type="human",
        actor_id=user.username,
        entity_type="mcp_server",
        entity_id=server.id,
        before_state=before,
        after_state={"enabled": server.enabled, "transport": server.transport},
    )
    await db.commit()
    await db.refresh(server)
    return _to_out(server, await _agents_using(db, server.name))


@router.delete("/{server_id}", status_code=204)
async def delete_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("ADMIN")),
) -> None:
    server = await db.get(McpServer, server_id)
    if server is None:
        raise HTTPException(404, "Servidor MCP não encontrado")
    in_use = await _agents_using(db, server.name)
    if in_use:
        raise HTTPException(
            409, f"Servidor em uso por: {', '.join(in_use)}. Remova o vínculo nos agentes primeiro."
        )
    await record_audit(
        db,
        event_type="config.changed",
        actor_type="human",
        actor_id=user.username,
        entity_type="mcp_server",
        entity_id=server.id,
        before_state={"name": server.name},
        after_state={"deleted": True},
    )
    await db.delete(server)
    await db.commit()


@router.post("/{server_id}/discover", response_model=McpServerOut)
async def discover_server_tools(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("ADMIN")),
) -> McpServerOut:
    """Conecta no servidor, faz o handshake e atualiza a lista de ferramentas."""
    server = await db.get(McpServer, server_id)
    if server is None:
        raise HTTPException(404, "Servidor MCP não encontrado")

    server.last_checked_at = datetime.now(timezone.utc)
    # Renova o access_token antes de usar, se estiver expirado.
    access_token = await mcp_oauth.ensure_fresh_token(server)
    try:
        result = await discover_tools(_to_config(server, access_token))
    except MCPAuthorizationRequired as exc:
        # Distingue "precisa autorizar" de falha genérica, para a UI oferecer
        # o botão de autorização em vez de só mostrar erro.
        server.last_status = "AUTH_REQUIRED"
        server.last_error = str(exc)[:MAX_ERROR_CHARS]
        metadata = dict(server.oauth_metadata or {})
        if exc.resource_metadata_url:
            metadata["resource_metadata_url"] = exc.resource_metadata_url
            server.oauth_metadata = metadata
        await db.commit()
        await db.refresh(server)
        return _to_out(server, await _agents_using(db, server.name))
    except MCPConnectionError as exc:
        server.last_status = "ERROR"
        server.last_error = str(exc)[:MAX_ERROR_CHARS]
        await db.commit()
        await db.refresh(server)
        return _to_out(server, await _agents_using(db, server.name))
    except Exception as exc:  # noqa: BLE001 - falha inesperada não deve derrubar a API
        server.last_status = "ERROR"
        server.last_error = f"{type(exc).__name__}: {exc}"[:MAX_ERROR_CHARS]
        await db.commit()
        await db.refresh(server)
        return _to_out(server, await _agents_using(db, server.name))

    server.tools = result["tools"]
    server.last_status = "OK"
    server.last_error = None
    await record_audit(
        db,
        event_type="config.changed",
        actor_type="human",
        actor_id=user.username,
        entity_type="mcp_server",
        entity_id=server.id,
        after_state={
            "discovered_tools": len(result["tools"]),
            "server_version": result.get("server_version"),
        },
    )
    await db.commit()
    await db.refresh(server)
    return _to_out(server, await _agents_using(db, server.name))


# ------------------------------ OAuth 2.1 ------------------------------
# Fluxo: /oauth/start devolve a URL de consentimento (descobrindo metadata e
# registrando o cliente dinamicamente na primeira vez); o provedor redireciona
# o navegador para /mcp/oauth/callback, que troca o código por tokens.


@router.post("/{server_id}/oauth/start", response_model=McpOAuthStartOut)
async def start_oauth(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("ADMIN")),
) -> McpOAuthStartOut:
    server = await db.get(McpServer, server_id)
    if server is None:
        raise HTTPException(404, "Servidor MCP não encontrado")
    hint = (server.oauth_metadata or {}).get("resource_metadata_url")
    try:
        url = await mcp_oauth.prepare_authorization(server, resource_metadata_url=hint)
    except MCPOAuthError as exc:
        raise HTTPException(422, str(exc)) from exc
    await record_audit(
        db,
        event_type="config.changed",
        actor_type="human",
        actor_id=user.username,
        entity_type="mcp_server",
        entity_id=server.id,
        after_state={"oauth": "authorization_started"},
    )
    await db.commit()
    return McpOAuthStartOut(authorization_url=url, redirect_uri=mcp_oauth.redirect_uri())


@router.post("/{server_id}/oauth/reset", response_model=McpServerOut)
async def reset_oauth(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("ADMIN")),
) -> McpServerOut:
    """Revoga localmente a autorização (apaga tokens); mantém o client_id."""
    server = await db.get(McpServer, server_id)
    if server is None:
        raise HTTPException(404, "Servidor MCP não encontrado")
    mcp_oauth.clear_authorization(server)
    if server.last_status == "OK":
        server.last_status = "AUTH_REQUIRED"
    await record_audit(
        db,
        event_type="config.changed",
        actor_type="human",
        actor_id=user.username,
        entity_type="mcp_server",
        entity_id=server.id,
        after_state={"oauth": "authorization_cleared"},
    )
    await db.commit()
    await db.refresh(server)
    return _to_out(server, await _agents_using(db, server.name))


# Router separado: o callback é acessado pelo NAVEGADOR (redirect do provedor
# OAuth), sem o header Authorization da API. A proteção é o `state`
# imprevisível gerado no start e casado com o servidor no banco — requisição
# sem state válido é rejeitada. Também fica fora do prefixo /mcp/servers.
oauth_router = APIRouter(prefix="/mcp/oauth", tags=["mcp"])


def _callback_page(title: str, message: str, ok: bool) -> HTMLResponse:
    color = "#16a34a" if ok else "#dc2626"
    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>{title}</title>
<style>
 body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#f8fafc;
 display:flex;align-items:center;justify-content:center;height:100vh;margin:0;color:#0f172a}}
 .card{{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:32px 40px;
 box-shadow:0 4px 6px -1px rgb(0 0 0/.08);max-width:520px;text-align:center}}
 h1{{font-size:18px;margin:0 0 8px;color:{color}}}
 p{{font-size:14px;color:#475569;margin:0}}
</style></head>
<body><div class="card"><h1>{title}</h1><p>{message}</p></div></body></html>"""
    return HTMLResponse(content=html, status_code=200 if ok else 400)


@oauth_router.get("/callback")
async def oauth_callback(
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Recebe o redirect do provedor OAuth e conclui a autorização."""
    if error:
        return _callback_page(
            "Autorização negada",
            f"O provedor retornou: {error}. {error_description or ''}".strip(),
            ok=False,
        )
    if not state or not code:
        return _callback_page(
            "Requisição inválida", "Parâmetros 'state' e 'code' são obrigatórios.", ok=False
        )

    server = (
        await db.execute(select(McpServer).where(McpServer.oauth_state == state))
    ).scalar_one_or_none()
    if server is None:
        # state desconhecido/expirado: possivelmente reuso de link antigo.
        return _callback_page(
            "Autorização expirada",
            "Não há autorização pendente para este link. Inicie o processo novamente na tela de MCP.",
            ok=False,
        )

    try:
        await mcp_oauth.complete_authorization(server, code)
    except MCPOAuthError as exc:
        server.last_status = "AUTH_REQUIRED"
        server.last_error = str(exc)[:MAX_ERROR_CHARS]
        await db.commit()
        return _callback_page("Falha na autorização", str(exc), ok=False)

    server.last_error = None
    await record_audit(
        db,
        event_type="config.changed",
        actor_type="human",
        actor_id="oauth-callback",
        entity_type="mcp_server",
        entity_id=server.id,
        after_state={"oauth": "authorized"},
    )
    await db.commit()
    return _callback_page(
        "Autorizado com sucesso",
        f"O servidor MCP '{server.name}' foi autorizado. "
        "Volte para a tela de MCP e rode a descoberta de ferramentas.",
        ok=True,
    )
