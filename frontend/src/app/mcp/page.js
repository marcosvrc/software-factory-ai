"use client";
import clsx from "clsx";
import {
  AlertTriangle,
  Plug,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShieldOff,
  Trash2,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input, Textarea } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { Toggle } from "@/components/ui/Toggle";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import { hasRole } from "@/lib/permissions";
import { useAuth } from "@/lib/useAuth";

const EMPTY_FORM = {
  name: "",
  description: "",
  transport: "stdio",
  command: "",
  args: "",
  url: "",
  env: "",
  headers: "",
  timeout_seconds: 30,
};

/** Converte "CHAVE=valor" por linha em objeto, ignorando linhas inválidas. */
function parseKeyValue(text) {
  const result = {};
  for (const line of (text || "").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const index = trimmed.indexOf("=");
    if (index <= 0) continue;
    result[trimmed.slice(0, index).trim()] = trimmed.slice(index + 1).trim();
  }
  return result;
}

function parseArgs(text) {
  return (text || "")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
}

function ServerFormModal({ open, onClose, onSaved }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const { notify } = useToast();
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });
  const isStdio = form.transport === "stdio";

  async function submit() {
    setSaving(true);
    try {
      await api("/mcp/servers", {
        method: "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          description: form.description || null,
          transport: form.transport,
          command: isStdio ? form.command.trim() : null,
          args: isStdio ? parseArgs(form.args) : [],
          url: isStdio ? null : form.url.trim(),
          env: parseKeyValue(form.env),
          headers: isStdio ? {} : parseKeyValue(form.headers),
          timeout_seconds: Number(form.timeout_seconds) || 30,
          enabled: false,
        }),
      });
      notify("Servidor MCP cadastrado. Faça a descoberta para listar as ferramentas.", {
        type: "success",
      });
      setForm(EMPTY_FORM);
      onSaved();
      onClose();
    } catch (e) {
      notify(`Não foi possível cadastrar: ${e.message}`, { type: "error" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title="Novo servidor MCP"
      description="O servidor nasce desabilitado; habilite depois de validar a conexão."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={submit}
            loading={saving}
            disabled={!form.name.trim() || (isStdio ? !form.command.trim() : !form.url.trim())}
          >
            Cadastrar
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-2.5 rounded-lg bg-warning-50 px-3.5 py-3 text-sm text-warning-800">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <p>
            Um servidor <strong>stdio</strong> é um comando executado dentro do container da API.
            Cadastre apenas servidores de origem confiável.
          </p>
        </div>

        <Input id="name" label="Nome" placeholder="ex.: github" value={form.name} onChange={set("name")} autoFocus />
        <Input
          id="description"
          label="Descrição"
          placeholder="Para que serve este servidor"
          value={form.description}
          onChange={set("description")}
        />

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-slate-700">Transporte</span>
          <div className="flex gap-2">
            {["stdio", "http"].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setForm({ ...form, transport: t })}
                className={clsx(
                  "rounded-lg border px-3 py-1.5 text-sm font-medium",
                  form.transport === t
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-slate-300 text-slate-600 hover:bg-slate-50"
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {isStdio ? (
          <>
            <Input
              id="command"
              label="Comando"
              placeholder="uvx"
              hint="Disponíveis no container: uvx, uv, npx, node, python3."
              value={form.command}
              onChange={set("command")}
            />
            <Textarea
              id="args"
              label="Argumentos"
              rows={3}
              hint="Um por linha. Ex.: mcp-server-git"
              value={form.args}
              onChange={set("args")}
            />
          </>
        ) : (
          <>
            <Input
              id="url"
              label="URL"
              placeholder="https://servidor/mcp"
              value={form.url}
              onChange={set("url")}
            />
            <Textarea
              id="headers"
              label="Headers"
              rows={3}
              hint="Um por linha, CHAVE=valor. Deixe vazio para servidores OAuth: a autorização é feita pelo botão Autorizar depois de cadastrar."
              value={form.headers}
              onChange={set("headers")}
            />
          </>
        )}

        <Textarea
          id="env"
          label="Variáveis de ambiente"
          rows={3}
          hint="Um por linha, CHAVE=valor. Valores não são exibidos depois de salvos."
          value={form.env}
          onChange={set("env")}
        />
        <Input
          id="timeout"
          label="Timeout (segundos)"
          type="number"
          min="1"
          max="300"
          value={form.timeout_seconds}
          onChange={set("timeout_seconds")}
        />
      </div>
    </Modal>
  );
}

function ToolsModal({ server, onClose }) {
  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      title={`Ferramentas de ${server.name}`}
      description={`${server.tools.length} ferramenta(s) descoberta(s)`}
    >
      {server.tools.length === 0 ? (
        <p className="text-sm text-slate-500">
          Nenhuma ferramenta descoberta ainda. Rode a descoberta neste servidor.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {server.tools.map((tool) => (
            <div key={tool.name} className="rounded-lg border border-slate-200 px-3.5 py-2.5">
              <div className="flex items-center gap-2">
                <Wrench size={13} className="text-slate-400" />
                <code className="text-sm font-medium text-slate-800">{tool.name}</code>
              </div>
              {tool.description && (
                <p className="mt-1 text-xs text-slate-500">{tool.description}</p>
              )}
              {Object.keys(tool.input_schema?.properties || {}).length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {Object.keys(tool.input_schema.properties).map((p) => (
                    <code key={p} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
                      {p}
                    </code>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

const STATUS_TONE = { OK: "success", ERROR: "danger", AUTH_REQUIRED: "warning" };
const STATUS_LABEL = { OK: "conectado", ERROR: "falha", AUTH_REQUIRED: "precisa autorizar" };

const AUTH_BADGE = {
  authorized: { tone: "success", label: "autorizado" },
  expired: { tone: "warning", label: "autorização expirada" },
  not_authorized: { tone: "neutral", label: "não autorizado" },
};

function ServerCard({
  server,
  canEdit,
  busy,
  onToggle,
  onDiscover,
  onDelete,
  onShowTools,
  onAuthorize,
  onResetAuth,
}) {
  const isHttp = server.transport === "http";
  const auth = AUTH_BADGE[server.auth_status];
  const needsAuth = isHttp && server.auth_status !== "authorized";
  return (
    <Card>
      <CardBody className="flex flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <Toggle
              checked={server.enabled}
              disabled={!canEdit || busy}
              onChange={(next) => onToggle(server, next)}
              label={`Habilitar ${server.name}`}
            />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className={clsx("font-medium", server.enabled ? "text-slate-900" : "text-slate-400")}>
                  {server.name}
                </span>
                <Badge tone="neutral">{server.transport}</Badge>
                {server.last_status && (
                  <Badge tone={STATUS_TONE[server.last_status] || "neutral"} dot>
                    {STATUS_LABEL[server.last_status] || server.last_status}
                  </Badge>
                )}
                {auth && <Badge tone={auth.tone}>{auth.label}</Badge>}
                {server.tools.length > 0 && (
                  <Badge tone="info">{server.tools.length} ferramenta(s)</Badge>
                )}
              </div>
              {server.description && (
                <p className="mt-0.5 text-sm text-slate-500">{server.description}</p>
              )}
              <p className="mt-1 truncate font-mono text-xs text-slate-400">
                {server.transport === "stdio"
                  ? [server.command, ...(server.args || [])].join(" ")
                  : server.url}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 gap-2">
            {server.tools.length > 0 && (
              <Button size="sm" variant="ghost" icon={Wrench} onClick={() => onShowTools(server)}>
                Ferramentas
              </Button>
            )}
            {canEdit && (
              <>
                {needsAuth && (
                  <Button
                    size="sm"
                    variant="primary"
                    icon={ShieldCheck}
                    loading={busy}
                    onClick={() => onAuthorize(server)}
                  >
                    Autorizar
                  </Button>
                )}
                {isHttp && server.auth_status === "authorized" && (
                  <Button size="sm" variant="ghost" icon={ShieldOff} onClick={() => onResetAuth(server)}>
                    Revogar
                  </Button>
                )}
                <Button size="sm" variant="secondary" icon={RefreshCw} loading={busy} onClick={() => onDiscover(server)}>
                  Descobrir
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  icon={Trash2}
                  onClick={() => onDelete(server)}
                  aria-label={`Remover ${server.name}`}
                />
              </>
            )}
          </div>
        </div>

        {(server.env_keys.length > 0 || server.header_keys.length > 0) && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
            <span>segredos configurados:</span>
            {[...server.env_keys, ...server.header_keys].map((k) => (
              <code key={k} className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
                {k}
              </code>
            ))}
          </div>
        )}

        {server.used_by_agents.length > 0 && (
          <p className="text-xs text-slate-500">
            Usado por: {server.used_by_agents.join(", ")}
          </p>
        )}

        {server.last_status === "ERROR" && server.last_error && (
          <pre className="max-h-32 overflow-auto whitespace-pre-wrap rounded-lg bg-danger-50 px-3 py-2 text-xs text-danger-700">
            {server.last_error}
          </pre>
        )}
      </CardBody>
    </Card>
  );
}

export default function McpPage() {
  const [servers, setServers] = useState(null);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [toolsOf, setToolsOf] = useState(null);
  const [awaitingAuthId, setAwaitingAuthId] = useState(null);
  const { notify } = useToast();
  const { user } = useAuth();
  const canEdit = hasRole(user, "ADMIN");

  async function load() {
    try {
      setServers(await api("/mcp/servers"));
    } catch (e) {
      notify(`Não foi possível carregar os servidores MCP: ${e.message}`, { type: "error" });
    }
  }

  useEffect(() => {
    load();
  }, []);

  // Enquanto o usuário conclui o consentimento em outra aba, recarrega o
  // estado periodicamente para refletir a autorização sem exigir refresh.
  useEffect(() => {
    if (!awaitingAuthId) return;
    const interval = setInterval(async () => {
      try {
        const data = await api("/mcp/servers");
        setServers(data);
        const target = data.find((s) => s.id === awaitingAuthId);
        if (target?.auth_status === "authorized") {
          setAwaitingAuthId(null);
          notify(`${target.name} autorizado. Rode a descoberta de ferramentas.`, {
            type: "success",
          });
        }
      } catch {
        // silencioso: é polling de conveniência
      }
    }, 3000);
    const stop = setTimeout(() => setAwaitingAuthId(null), 5 * 60 * 1000);
    return () => {
      clearInterval(interval);
      clearTimeout(stop);
    };
  }, [awaitingAuthId, notify]);

  async function toggle(server, enabled) {
    setBusyId(server.id);
    try {
      await api(`/mcp/servers/${server.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      });
      await load();
    } catch (e) {
      notify(`Não foi possível alterar: ${e.message}`, { type: "error" });
    } finally {
      setBusyId(null);
    }
  }

  async function discover(server) {
    setBusyId(server.id);
    try {
      const updated = await api(`/mcp/servers/${server.id}/discover`, { method: "POST" });
      if (updated.last_status === "OK") {
        notify(`${updated.tools.length} ferramenta(s) descoberta(s) em ${server.name}.`, {
          type: "success",
        });
      } else if (updated.last_status === "AUTH_REQUIRED") {
        notify(`${server.name} exige autorização. Use o botão "Autorizar".`, { type: "warning" });
      } else {
        notify(`Falha ao conectar em ${server.name}. Veja o detalhe no card.`, { type: "error" });
      }
      await load();
    } catch (e) {
      notify(`Falha na descoberta: ${e.message}`, { type: "error" });
    } finally {
      setBusyId(null);
    }
  }

  async function authorize(server) {
    setBusyId(server.id);
    try {
      const { authorization_url } = await api(`/mcp/servers/${server.id}/oauth/start`, {
        method: "POST",
      });
      // Abre o consentimento do provedor em nova aba; a conclusão acontece no
      // callback da API, então aqui só orientamos e recarregamos o estado.
      window.open(authorization_url, "_blank", "noopener,noreferrer");
      notify(
        "Autorize o acesso na aba aberta e depois volte aqui para rodar a descoberta.",
        { type: "info", duration: 9000 }
      );
      setAwaitingAuthId(server.id);
    } catch (e) {
      notify(`Não foi possível iniciar a autorização: ${e.message}`, { type: "error" });
    } finally {
      setBusyId(null);
    }
  }

  async function resetAuth(server) {
    if (!window.confirm(`Revogar a autorização de "${server.name}"? Será necessário autorizar novamente.`))
      return;
    setBusyId(server.id);
    try {
      await api(`/mcp/servers/${server.id}/oauth/reset`, { method: "POST" });
      notify("Autorização revogada.", { type: "success" });
      await load();
    } catch (e) {
      notify(`Não foi possível revogar: ${e.message}`, { type: "error" });
    } finally {
      setBusyId(null);
    }
  }

  async function remove(server) {
    if (!window.confirm(`Remover o servidor MCP "${server.name}"?`)) return;
    setBusyId(server.id);
    try {
      await api(`/mcp/servers/${server.id}`, { method: "DELETE" });
      notify("Servidor removido.", { type: "success" });
      await load();
    } catch (e) {
      notify(`Não foi possível remover: ${e.message}`, { type: "error" });
    } finally {
      setBusyId(null);
    }
  }

  const loading = servers === null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Servidores MCP</h1>
          <p className="mt-1 text-sm text-slate-500">
            Cadastre servidores Model Context Protocol e descubra as ferramentas que eles expõem.
            O vínculo com cada agente é feito na tela de Agentes.
          </p>
        </div>
        {canEdit && (
          <Button variant="primary" icon={Plus} onClick={() => setCreating(true)}>
            Novo servidor
          </Button>
        )}
      </div>

      <div className="flex items-start gap-2.5 rounded-lg border border-info-200 bg-info-50 px-3.5 py-3 text-sm text-info-800">
        <Plug size={16} className="mt-0.5 shrink-0" />
        <p>
          Nesta fase os agentes ainda não executam ferramentas MCP durante as execuções: aqui você
          configura e valida os servidores. A execução automática pelos agentes é a próxima etapa.
        </p>
      </div>

      {!canEdit && (
        <p className="rounded-lg bg-warning-50 px-3.5 py-2.5 text-sm text-warning-700">
          Você tem acesso somente de leitura. Configurar servidores MCP requer o papel
          Administrador.
        </p>
      )}

      {loading ? (
        <div className="flex flex-col gap-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : servers.length === 0 ? (
        <EmptyState
          icon={Plug}
          title="Nenhum servidor MCP cadastrado"
          description="Cadastre um servidor para expor ferramentas externas aos agentes da fábrica."
          action={
            canEdit && (
              <Button variant="primary" icon={Plus} onClick={() => setCreating(true)}>
                Cadastrar servidor
              </Button>
            )
          }
        />
      ) : (
        <div className="flex flex-col gap-3">
          {servers.map((server) => (
            <ServerCard
              key={server.id}
              server={server}
              canEdit={canEdit}
              busy={busyId === server.id}
              onToggle={toggle}
              onDiscover={discover}
              onDelete={remove}
              onShowTools={setToolsOf}
              onAuthorize={authorize}
              onResetAuth={resetAuth}
            />
          ))}
        </div>
      )}

      <ServerFormModal open={creating} onClose={() => setCreating(false)} onSaved={load} />
      {toolsOf && <ToolsModal server={toolsOf} onClose={() => setToolsOf(null)} />}
    </div>
  );
}
