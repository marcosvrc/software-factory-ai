"use client";
import {
  Background,
  ReactFlow,
  ReactFlowProvider,
  MarkerType,
  Panel,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo } from "react";
import { PROCESS_EDGES, PROCESS_NODES, NODE_KIND } from "@/lib/processDiagram";
import { EndNode, GateNode, StageNode } from "./CustomNodes";
import { EDGE_KIND_STYLE } from "./nodeStyles";

const NODE_TYPES = { stage: StageNode, gate: GateNode, end: EndNode };

function buildFlowNodes(nodeState) {
  return PROCESS_NODES.map((n) => ({
    id: n.id,
    type: n.kind === NODE_KIND.END ? "end" : n.kind === NODE_KIND.GATE ? "gate" : "stage",
    position: { x: n.x, y: n.y },
    draggable: false,
    selectable: false,
    data: {
      label: n.label,
      status: nodeState[n.id]?.status || "pending",
      cycles: nodeState[n.id]?.cycles || 0,
      kind: n.id,
    },
  }));
}

function buildFlowEdges(nodeState, activeNodeId, escalatedGate) {
  return PROCESS_EDGES.filter((e) => {
    // Esconde as arestas de retomada não relevantes ao gate escalado atual,
    // para não poluir o diagrama com 9 linhas saindo de human_review.
    if (e.kind === "resume") {
      return escalatedGate ? e.gate === escalatedGate : false;
    }
    return true;
  }).map((e) => {
    const style = EDGE_KIND_STYLE[e.kind];
    const isOnActivePath =
      (e.source === activeNodeId && (nodeState[e.target]?.status === "active" || nodeState[e.target]?.status === "waiting")) ||
      (e.kind === "resume" && activeNodeId === "human_review");
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.source === "architecture" && e.kind !== "happy" ? "side" : undefined,
      label: e.label,
      animated: isOnActivePath,
      style: {
        stroke: isOnActivePath ? "#4f46e5" : style.stroke,
        strokeWidth: isOnActivePath ? 2.5 : style.strokeWidth,
        strokeDasharray: style.dashed ? "5 4" : undefined,
      },
      labelStyle: { fontSize: 10, fill: "#64748b" },
      labelBgStyle: { fill: "#f8fafc" },
      markerEnd: { type: MarkerType.ArrowClosed, color: isOnActivePath ? "#4f46e5" : style.stroke, width: 16, height: 16 },
      type: "smoothstep",
    };
  });
}

function DiagramInner({ nodeState, currentNodeId, escalatedGate }) {
  const initialNodes = useMemo(() => buildFlowNodes(nodeState), [nodeState]);
  const initialEdges = useMemo(
    () => buildFlowEdges(nodeState, currentNodeId, escalatedGate),
    [nodeState, currentNodeId, escalatedGate]
  );
  const [nodes, setNodes] = useNodesState(initialNodes);
  const [edges, setEdges] = useEdgesState(initialEdges);

  useEffect(() => setNodes(initialNodes), [initialNodes, setNodes]);
  useEffect(() => setEdges(initialEdges), [initialEdges, setEdges]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      minZoom={0.3}
      maxZoom={1.5}
      proOptions={{ hideAttribution: true }}
      nodesConnectable={false}
      nodesDraggable={false}
      elementsSelectable={false}
      panOnScroll
    >
      <Background color="#e2e8f0" gap={20} />
      <Panel position="bottom-left" className="!m-0">
        <Legend />
      </Panel>
    </ReactFlow>
  );
}

function Legend() {
  const items = [
    { tone: "bg-info-500", label: "Em andamento" },
    { tone: "bg-warning-500", label: "Aguardando decisão / ajuste" },
    { tone: "bg-success-500", label: "Concluído" },
    { tone: "bg-danger-500", label: "Escalado / cancelado" },
    { tone: "bg-slate-300", label: "Pendente" },
  ];
  return (
    <div className="flex flex-wrap gap-3 rounded-lg border border-slate-200 bg-white/90 px-3 py-2 text-[11px] text-slate-600 shadow-sm backdrop-blur">
      {items.map((item) => (
        <span key={item.label} className="flex items-center gap-1.5">
          <span className={`h-2 w-2 rounded-full ${item.tone}`} />
          {item.label}
        </span>
      ))}
    </div>
  );
}

/** Diagrama estilo "Camunda Cockpit" do processo software_delivery: desenha
 * todas as etapas/gates reais do grafo (orchestrator/graphs/software_delivery.py)
 * e destaca em qual delas a execução atual está parada, incluindo ciclos de
 * ajuste e escaladas para revisão humana. */
export function ProcessDiagram({ nodeState, currentNodeId, escalatedGate, height = 720 }) {
  return (
    <div style={{ height }} className="w-full overflow-hidden rounded-xl2 border border-slate-200 bg-slate-50">
      <ReactFlowProvider>
        <DiagramInner nodeState={nodeState} currentNodeId={currentNodeId} escalatedGate={escalatedGate} />
      </ReactFlowProvider>
    </div>
  );
}
