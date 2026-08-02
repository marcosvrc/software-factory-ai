"use client";
import { FolderKanban, Plus, Play, ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input, Textarea } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";

const PROJECT_STATUS_TONE = {
  DRAFT: "neutral",
  ACTIVE: "brand",
  ON_HOLD: "warning",
  COMPLETED: "success",
  ARCHIVED: "neutral",
};

function NewProjectModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState({ name: "", description: "" });
  const [saving, setSaving] = useState(false);
  const { notify } = useToast();

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await api("/projects", { method: "POST", body: JSON.stringify(form) });
      notify("Projeto criado com sucesso.", { type: "success" });
      setForm({ name: "", description: "" });
      onCreated();
      onClose();
    } catch (err) {
      notify(`Não foi possível criar o projeto: ${err.message}`, { type: "error" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Novo projeto"
      description="Um projeto agrupa demandas que compartilham o mesmo workspace de código."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={saving} disabled={!form.name.trim()}>
            Criar projeto
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          id="project-name"
          label="Nome"
          placeholder="Ex.: Portal do cliente"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          autoFocus
        />
        <Textarea
          id="project-description"
          label="Descrição"
          placeholder="Contexto breve sobre o objetivo do projeto"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </form>
    </Modal>
  );
}

function NewDemandModal({ open, onClose, project, onCreated }) {
  const [form, setForm] = useState({ title: "", description: "" });
  const [saving, setSaving] = useState(false);
  const { notify } = useToast();

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await api(`/projects/${project.id}/demands`, { method: "POST", body: JSON.stringify(form) });
      notify("Demanda registrada.", { type: "success" });
      setForm({ title: "", description: "" });
      onCreated();
      onClose();
    } catch (err) {
      notify(`Não foi possível registrar a demanda: ${err.message}`, { type: "error" });
    } finally {
      setSaving(false);
    }
  }

  if (!project) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Nova demanda em "${project.name}"`}
      description="Descreva o que precisa ser desenvolvido. Quanto mais contexto, melhor a análise inicial."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={saving} disabled={!form.title.trim()}>
            Registrar demanda
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          id="demand-title"
          label="Título"
          placeholder="Ex.: Cadastro de produtos com importação em lote"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          autoFocus
        />
        <Textarea
          id="demand-description"
          label="Descrição"
          rows={4}
          placeholder="Canal de acesso, escopo, volume esperado, regras de negócio essenciais…"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </form>
    </Modal>
  );
}

function ProjectCard({ project, demands, expanded, onToggle, onAddDemand, onStartRun, startingId }) {
  return (
    <Card>
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown size={16} className="text-slate-400" /> : <ChevronRight size={16} className="text-slate-400" />}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900">{project.name}</span>
              <Badge tone={PROJECT_STATUS_TONE[project.status] || "neutral"}>{project.status}</Badge>
            </div>
            {project.description && <p className="mt-0.5 text-sm text-slate-500">{project.description}</p>}
          </div>
        </div>
        <span className="shrink-0 text-xs text-slate-400">{(demands || []).length} demanda(s)</span>
      </button>

      {expanded && (
        <CardBody className="border-t border-slate-100 pt-4">
          {(demands || []).length === 0 ? (
            <p className="text-sm text-slate-500">Nenhuma demanda registrada ainda.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {demands.map((d) => (
                <li
                  key={d.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50/60 px-3.5 py-2.5"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-800">{d.title}</p>
                    <p className="text-xs text-slate-500">{d.status}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    icon={Play}
                    loading={startingId === d.id}
                    onClick={() => onStartRun(d.id)}
                  >
                    Iniciar
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <Button size="sm" variant="ghost" icon={Plus} className="mt-3" onClick={onAddDemand}>
            Nova demanda
          </Button>
        </CardBody>
      )}
    </Card>
  );
}

export default function Projects() {
  const [projects, setProjects] = useState(null);
  const [demands, setDemands] = useState({});
  const [expandedId, setExpandedId] = useState(null);
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [demandModalProject, setDemandModalProject] = useState(null);
  const [startingId, setStartingId] = useState(null);
  const { notify } = useToast();

  async function load() {
    try {
      const p = await api("/projects");
      setProjects(p);
      const entries = await Promise.all(p.map(async (project) => [project.id, await api(`/projects/${project.id}/demands`)]));
      setDemands(Object.fromEntries(entries));
    } catch (e) {
      notify(`Não foi possível carregar projetos: ${e.message}`, { type: "error" });
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function startRun(demandId) {
    setStartingId(demandId);
    try {
      const run = await api(`/demands/${demandId}/runs`, { method: "POST" });
      notify("Execução iniciada.", { type: "success" });
      window.location.href = `/runs/${run.id}`;
    } catch (err) {
      notify(`Não foi possível iniciar a execução: ${err.message}`, { type: "error" });
    } finally {
      setStartingId(null);
    }
  }

  const loading = projects === null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Projetos</h1>
          <p className="mt-1 text-sm text-slate-500">Organize demandas e dispare execuções da fábrica.</p>
        </div>
        <Button variant="primary" icon={Plus} onClick={() => setNewProjectOpen(true)}>
          Novo projeto
        </Button>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="Nenhum projeto criado ainda"
          description="Crie o primeiro projeto para começar a registrar demandas e disparar execuções."
          action={
            <Button variant="primary" icon={Plus} onClick={() => setNewProjectOpen(true)}>
              Criar projeto
            </Button>
          }
        />
      ) : (
        <div className="flex flex-col gap-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              demands={demands[project.id]}
              expanded={expandedId === project.id}
              onToggle={() => setExpandedId(expandedId === project.id ? null : project.id)}
              onAddDemand={() => setDemandModalProject(project)}
              onStartRun={startRun}
              startingId={startingId}
            />
          ))}
        </div>
      )}

      <NewProjectModal open={newProjectOpen} onClose={() => setNewProjectOpen(false)} onCreated={load} />
      <NewDemandModal
        open={!!demandModalProject}
        project={demandModalProject}
        onClose={() => setDemandModalProject(null)}
        onCreated={load}
      />
    </div>
  );
}
