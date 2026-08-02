"use client";
import clsx from "clsx";
import { Bot, RotateCcw, Search, Settings2, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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
import { STAGE_LABELS } from "@/lib/statuses";
import { useAuth } from "@/lib/useAuth";
import {
  DOMAIN_LABELS,
  DOMAIN_ORDER,
  buildConfiguration,
  formFromConfiguration,
} from "@/lib/agents";

const TABS = [
  ["general", "Geral"],
  ["model", "Modelo"],
  ["tools", "Ferramentas"],
  ["mcp", "MCP"],
  ["prompt", "Prompt"],
];

function AgentEditor({ agent, baseTemplate, placeholders, mcpServers, onClose, onSaved, canEdit }) {
  const [form, setForm] = useState(() => formFromConfiguration(agent.configuration || {}));
  const [selectedMcp, setSelectedMcp] = useState(
    () => new Set((agent.configuration || {}).mcp_servers || [])
  );
  const [tab, setTab] = useState("general");
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const { notify } = useToast();

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  function toggleMcp(name) {
    const next = new Set(selectedMcp);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setSelectedMcp(next);
  }

  async function save() {
    setSaving(true);
    try {
      const configuration = buildConfiguration(agent.configuration || {}, form);
      if (selectedMcp.size > 0) configuration.mcp_servers = [...selectedMcp].sort();
      else delete configuration.mcp_servers;
      await api(`/agents/${agent.id}`, {
        method: "PATCH",
        body: JSON.stringify({ configuration }),
      });
      notify("Configuração salva. Vale para as próximas execuções.", { type: "success" });
      onSaved();
      onClose();
    } catch (e) {
      notify(`Não foi possível salvar: ${e.message}`, { type: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function reset() {
    if (!window.confirm("Restaurar a configuração padrão deste agente? A customização atual será perdida.")) return;
    setResetting(true);
    try {
      await api(`/agents/${agent.id}/reset`, { method: "POST" });
      notify("Configuração padrão restaurada.", { type: "success" });
      onSaved();
      onClose();
    } catch (e) {
      notify(`Não foi possível restaurar: ${e.message}`, { type: "error" });
    } finally {
      setResetting(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      title={agent.name}
      description={`${agent.id} · ${DOMAIN_LABELS[agent.domain] || agent.domain}`}
      footer={
        <>
          {agent.customized && canEdit && (
            <Button variant="ghost" icon={RotateCcw} onClick={reset} loading={resetting} className="mr-auto">
              Restaurar padrão
            </Button>
          )}
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" onClick={save} loading={saving} disabled={!canEdit}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex gap-1.5 border-b border-slate-200 pb-px">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={clsx(
                "rounded-t-md px-3 py-1.5 text-sm font-medium transition-colors",
                tab === key
                  ? "border-b-2 border-brand-600 text-brand-700"
                  : "text-slate-500 hover:text-slate-700"
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "general" && (
          <>
            <Textarea
              id="objective"
              label="Objetivo"
              rows={5}
              hint="Instrução principal do agente; entra na seção OBJETIVO do prompt."
              value={form.objective}
              onChange={set("objective")}
              disabled={!canEdit}
            />
            <Textarea
              id="responsibilities"
              label="Responsabilidades"
              rows={5}
              hint="Uma por linha."
              value={form.responsibilities}
              onChange={set("responsibilities")}
              disabled={!canEdit}
            />
            <Textarea
              id="quality-gates"
              label="Critérios de qualidade"
              rows={4}
              hint="Uma por linha."
              value={form.qualityGates}
              onChange={set("qualityGates")}
              disabled={!canEdit}
            />
          </>
        )}

        {tab === "model" && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Input id="provider" label="Provider" value={form.provider} onChange={set("provider")} disabled={!canEdit} />
              <Input
                id="primary"
                label="Modelo primário"
                hint="Use a tag completa (ex.: qwen2.5-coder:7b)."
                value={form.primary}
                onChange={set("primary")}
                disabled={!canEdit}
              />
              <Input id="fallback" label="Modelo de fallback" value={form.fallback} onChange={set("fallback")} disabled={!canEdit} />
              <Input
                id="temperature"
                label="Temperatura"
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={form.temperature}
                onChange={set("temperature")}
                disabled={!canEdit}
              />
              <Input
                id="max-context"
                label="Máx. tokens de contexto"
                type="number"
                value={form.maxContextTokens}
                onChange={set("maxContextTokens")}
                disabled={!canEdit}
              />
            </div>
            <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
              Modelos precisam existir no Ollama local. Sem a tag, o runtime resolve a tag padrão
              conhecida; um nome inexistente faz o agente falhar com 404.
            </p>
          </>
        )}

        {tab === "tools" && (
          <>
            <Textarea
              id="allowed-tools"
              label="Ferramentas permitidas"
              rows={7}
              hint="Uma por linha."
              value={form.allowedTools}
              onChange={set("allowedTools")}
              disabled={!canEdit}
            />
            <Textarea
              id="denied-tools"
              label="Ferramentas negadas"
              rows={4}
              hint="Uma por linha. A negação prevalece sobre a permissão."
              value={form.deniedTools}
              onChange={set("deniedTools")}
              disabled={!canEdit}
            />
          </>
        )}

        {tab === "mcp" && (
          <>
            <p className="text-sm text-slate-500">
              Servidores MCP que este agente poderá usar. A execução das ferramentas pelos agentes
              é a próxima etapa; aqui você já define o vínculo.
            </p>
            {mcpServers.length === 0 ? (
              <p className="rounded-lg bg-slate-50 px-3.5 py-3 text-sm text-slate-500">
                Nenhum servidor MCP cadastrado. Cadastre em <strong>MCP</strong> no menu lateral.
              </p>
            ) : (
              <div className="flex flex-col gap-2">
                {mcpServers.map((server) => (
                  <label
                    key={server.id}
                    className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 px-3.5 py-2.5 hover:bg-slate-50"
                  >
                    <input
                      type="checkbox"
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                      checked={selectedMcp.has(server.name)}
                      disabled={!canEdit}
                      onChange={() => toggleMcp(server.name)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-slate-800">{server.name}</span>
                        {!server.enabled && <Badge tone="neutral">desabilitado</Badge>}
                        {server.tools?.length > 0 && (
                          <Badge tone="info">{server.tools.length} ferramenta(s)</Badge>
                        )}
                      </span>
                      {server.description && (
                        <span className="mt-0.5 block text-xs text-slate-500">
                          {server.description}
                        </span>
                      )}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </>
        )}

        {tab === "prompt" && (
          <>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-slate-500">
                Em branco, o agente usa o template base compartilhado. Preencha para customizar
                apenas este agente.
              </p>
              {canEdit && (
                <Button
                  size="sm"
                  variant="secondary"
                  icon={Sparkles}
                  onClick={() => setForm({ ...form, promptTemplate: baseTemplate })}
                >
                  Partir do base
                </Button>
              )}
            </div>
            <Textarea
              id="prompt-template"
              label="Prompt customizado"
              rows={16}
              className="font-mono text-xs"
              value={form.promptTemplate}
              onChange={set("promptTemplate")}
              disabled={!canEdit}
            />
            <div>
              <p className="mb-1.5 text-xs font-medium text-slate-600">Placeholders disponíveis</p>
              <div className="flex flex-wrap gap-1.5">
                {(placeholders || []).map((p) => (
                  <code
                    key={p}
                    className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600"
                  >
                    {`{${p}}`}
                  </code>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

function AgentRow({ agent, onToggle, onOpen, canEdit, busy }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 last:border-0">
      <div className="flex min-w-0 items-center gap-3">
        <Toggle
          checked={agent.enabled}
          disabled={!canEdit || busy}
          onChange={(next) => onToggle(agent, next)}
          label={`Habilitar ${agent.name}`}
        />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={clsx("text-sm font-medium", agent.enabled ? "text-slate-900" : "text-slate-400")}>
              {agent.name}
            </span>
            {agent.customized && <Badge tone="brand">customizado</Badge>}
            {(agent.configuration?.prompt_template || "").trim() && (
              <Badge tone="info">prompt próprio</Badge>
            )}
            {agent.configuration?.mcp_servers?.length > 0 && (
              <Badge tone="info">
                MCP: {agent.configuration.mcp_servers.length}
              </Badge>
            )}
            {agent.stages?.length === 0 && <Badge tone="neutral">fora do pipeline</Badge>}
          </div>
          <p className="truncate text-xs text-slate-400">
            {agent.id}
            {agent.stages?.length > 0 && (
              <> · {agent.stages.map((s) => STAGE_LABELS[s] || s).join(", ")}</>
            )}
          </p>
        </div>
      </div>
      <Button size="sm" variant="secondary" icon={Settings2} onClick={() => onOpen(agent)}>
        Configurar
      </Button>
    </div>
  );
}

export default function AgentsPage() {
  const [agents, setAgents] = useState(null);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [prompt, setPrompt] = useState({ template: "", placeholders: [] });
  const [mcpServers, setMcpServers] = useState([]);
  const { notify } = useToast();
  const { user } = useAuth();
  const canEdit = hasRole(user, "FACTORY_MANAGER");

  async function load() {
    try {
      setAgents(await api("/agents"));
    } catch (e) {
      notify(`Não foi possível carregar os agentes: ${e.message}`, { type: "error" });
    }
  }

  useEffect(() => {
    load();
    api("/agents/prompt-template")
      .then(setPrompt)
      .catch(() => {});
    api("/mcp/servers")
      .then(setMcpServers)
      .catch(() => {});
  }, []);

  async function toggle(agent, enabled) {
    setBusyId(agent.id);
    try {
      await api(`/agents/${agent.id}`, { method: "PATCH", body: JSON.stringify({ enabled }) });
      setAgents((prev) => prev.map((a) => (a.id === agent.id ? { ...a, enabled } : a)));
      notify(
        enabled
          ? `${agent.name} habilitado.`
          : `${agent.name} desabilitado; será ignorado nas próximas execuções.`,
        { type: "success" }
      );
    } catch (e) {
      notify(`Não foi possível alterar: ${e.message}`, { type: "error" });
    } finally {
      setBusyId(null);
    }
  }

  const grouped = useMemo(() => {
    if (!agents) return [];
    const term = query.trim().toLowerCase();
    const filtered = term
      ? agents.filter(
          (a) =>
            a.name.toLowerCase().includes(term) ||
            a.id.toLowerCase().includes(term) ||
            (a.configuration?.objective || "").toLowerCase().includes(term)
        )
      : agents;
    const byDomain = {};
    for (const agent of filtered) (byDomain[agent.domain] ||= []).push(agent);
    return DOMAIN_ORDER.filter((d) => byDomain[d]?.length).map((domain) => ({
      domain,
      agents: byDomain[domain],
    }));
  }, [agents, query]);

  const loading = agents === null;
  const enabledCount = agents?.filter((a) => a.enabled).length ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Agentes</h1>
          <p className="mt-1 text-sm text-slate-500">
            Escolha quais agentes participam do pipeline e ajuste objetivo, modelo, ferramentas e
            prompt de cada um.
          </p>
        </div>
        {!loading && (
          <div className="text-right text-sm text-slate-500">
            <span className="font-semibold text-slate-900">{enabledCount}</span> de {agents.length}{" "}
            habilitados
          </div>
        )}
      </div>

      {!canEdit && (
        <p className="rounded-lg bg-warning-50 px-3.5 py-2.5 text-sm text-warning-700">
          Você tem acesso somente de leitura. Alterar a configuração de agentes requer o papel
          Gestor da fábrica ou superior.
        </p>
      )}

      <Input
        id="search"
        placeholder="Buscar por nome, id ou objetivo…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {loading ? (
        <div className="flex flex-col gap-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : grouped.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="Nenhum agente encontrado"
          description="Ajuste a busca para ver os agentes disponíveis."
        />
      ) : (
        grouped.map(({ domain, agents: domainAgents }) => (
          <div key={domain}>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
              {DOMAIN_LABELS[domain] || domain}
              <span className="ml-2 font-normal normal-case text-slate-400">
                {domainAgents.filter((a) => a.enabled).length}/{domainAgents.length}
              </span>
            </h2>
            <Card className="overflow-hidden">
              {domainAgents.map((agent) => (
                <AgentRow
                  key={agent.id}
                  agent={agent}
                  canEdit={canEdit}
                  busy={busyId === agent.id}
                  onToggle={toggle}
                  onOpen={setEditing}
                />
              ))}
            </Card>
          </div>
        ))
      )}

      {editing && (
        <AgentEditor
          agent={editing}
          baseTemplate={prompt.template}
          placeholders={prompt.placeholders}
          mcpServers={mcpServers}
          canEdit={canEdit}
          onClose={() => setEditing(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}
