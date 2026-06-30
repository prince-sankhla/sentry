"use client";

import dagre from "dagre";
import {
  Background,
  BackgroundVariant,
  Controls,
  Edge,
  Handle,
  MarkerType,
  MiniMap,
  Node,
  NodeProps,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow
} from "@xyflow/react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Archive, Award, Building2, Crosshair, FileSearch, FileText, Filter, FolderTree, Globe2, Landmark, Maximize2, Search, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import type { GraphEdgeType, GraphNodeType, RelationshipGraph, RelationshipGraphNode } from "@/lib/api";

type SelectedItem = { kind: "node"; id: string } | { kind: "edge"; id: string } | null;

export type RelationshipGraphSelection =
  | { kind: "node"; node: RelationshipGraphNode }
  | { kind: "edge"; edge: RelationshipGraph["edges"][number] }
  | null;

type FlowNodeData = {
  graphNode: RelationshipGraphNode;
  selected: boolean;
  connected: boolean;
  dimmed: boolean;
  matched: boolean;
};

const typeLabels: Record<GraphNodeType, string> = {
  company: "Company",
  tender: "Tender",
  award: "Award",
  buyer: "Buyer",
  indicator: "Procurement Indicator",
  evidence: "Evidence",
  document: "Document",
  web_evidence: "Web Evidence",
  organization: "Organization",
  category: "Category"
};

const nodeStyles: Record<GraphNodeType, { border: string; fill: string; accent: string }> = {
  company: { border: "#667A52", fill: "#141D1A", accent: "#8DA175" },
  tender: { border: "#8B939E", fill: "#14191F", accent: "#E6E8EB" },
  award: { border: "#7A705F", fill: "#1D1A16", accent: "#C8CDD3" },
  buyer: { border: "#2A3441", fill: "#171F2A", accent: "#C8CDD3" },
  indicator: { border: "#C58B2A", fill: "#1F1A12", accent: "#F3D59A" },
  evidence: { border: "#8B939E", fill: "#15191D", accent: "#C8CDD3" },
  document: { border: "#5F6975", fill: "#14191F", accent: "#C8CDD3" },
  web_evidence: { border: "#5F6975", fill: "#111A1A", accent: "#C8CDD3" },
  organization: { border: "#667A52", fill: "#141D1A", accent: "#8DA175" },
  category: { border: "#7A705F", fill: "#1D1A16", accent: "#C8CDD3" }
};

const nodeThemeClasses: Record<GraphNodeType, { border: string; fill: string; accent: string }> = {
  company: { border: "border-[#667A52]", fill: "bg-[#141D1A]", accent: "text-[#8DA175]" },
  tender: { border: "border-[#8B939E]", fill: "bg-[#14191F]", accent: "text-[#E6E8EB]" },
  award: { border: "border-[#7A705F]", fill: "bg-[#1D1A16]", accent: "text-[#C8CDD3]" },
  buyer: { border: "border-[#2A3441]", fill: "bg-[#171F2A]", accent: "text-[#C8CDD3]" },
  indicator: { border: "border-[#C58B2A]", fill: "bg-[#1F1A12]", accent: "text-[#F3D59A]" },
  evidence: { border: "border-[#8B939E]", fill: "bg-[#15191D]", accent: "text-[#C8CDD3]" },
  document: { border: "border-[#5F6975]", fill: "bg-[#14191F]", accent: "text-[#C8CDD3]" },
  web_evidence: { border: "border-[#5F6975]", fill: "bg-[#111A1A]", accent: "text-[#C8CDD3]" },
  organization: { border: "border-[#667A52]", fill: "bg-[#141D1A]", accent: "text-[#8DA175]" },
  category: { border: "border-[#7A705F]", fill: "bg-[#1D1A16]", accent: "text-[#C8CDD3]" }
};

const edgeColors: Record<GraphEdgeType, string> = {
  company_tender: "#667A52",
  tender_award: "#C58B2A",
  award_company: "#A56A1F",
  buyer_tender: "#9AA4AF",
  buyer_company: "#9AA4AF",
  tender_indicator: "#C58B2A",
  company_indicator: "#C58B2A",
  evidence_indicator: "#C58B2A",
  tender_evidence: "#C8CDD3",
  web_evidence_company: "#C8CDD3",
  web_evidence_tender: "#C8CDD3",
  web_evidence_award: "#C8CDD3",
  document_tender: "#C8CDD3",
  category_tender: "#9AA4AF",
  organization_evidence: "#9AA4AF"
};

const filterTypes: GraphNodeType[] = ["company", "buyer", "tender", "award", "indicator", "evidence", "document", "web_evidence", "organization", "category"];

const nodeTypes = {
  investigation: InvestigationNode
};

export function RelationshipGraphExplorer({
  graph,
  onSelectionChange,
  showDetailsPanel = true
}: {
  graph: RelationshipGraph;
  onSelectionChange?: (selection: RelationshipGraphSelection) => void;
  showDetailsPanel?: boolean;
}) {
  return (
    <ReactFlowProvider>
      <RelationshipGraphCanvas graph={graph} onSelectionChange={onSelectionChange} showDetailsPanel={showDetailsPanel} />
    </ReactFlowProvider>
  );
}

function RelationshipGraphCanvas({
  graph,
  onSelectionChange,
  showDetailsPanel = true
}: {
  graph: RelationshipGraph;
  onSelectionChange?: (selection: RelationshipGraphSelection) => void;
  showDetailsPanel?: boolean;
}) {
  const [enabledTypes, setEnabledTypes] = useState<Set<GraphNodeType>>(() => new Set(filterTypes));
  const visibleGraph = useMemo(() => filterGraphByType(graph, enabledTypes), [enabledTypes, graph]);
  const initialNodes = useMemo(() => toFlowNodes(visibleGraph), [visibleGraph]);
  const initialEdges = useMemo(() => toFlowEdges(visibleGraph), [visibleGraph]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedItem, setSelectedItem] = useState<SelectedItem>(null);
  const [query, setQuery] = useState("");
  const { fitView, setCenter } = useReactFlow();

  const selectedNode = selectedItem?.kind === "node" ? visibleGraph.nodes.find((node) => node.id === selectedItem.id) : null;
  const selectedEdge = selectedItem?.kind === "edge" ? visibleGraph.edges.find((edge) => edge.id === selectedItem.id) : null;

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    setSelectedItem(null);
    onSelectionChange?.(null);
  }, [initialEdges, initialNodes, setEdges, setNodes]);

  function applySelection(nextSelection: SelectedItem, matches = new Set<string>()) {
    setSelectedItem(nextSelection);
    const connectedNodeIds = getConnectedNodeIds(visibleGraph, nextSelection);
    setNodes((current) => applyNodeHighlights(current, nextSelection?.kind === "node" ? nextSelection.id : null, connectedNodeIds, matches));
    setEdges((current) => applyEdgeHighlights(current, visibleGraph, nextSelection));

    if (nextSelection?.kind === "node") {
      const node = visibleGraph.nodes.find((candidate) => candidate.id === nextSelection.id) ?? null;
      onSelectionChange?.(node ? { kind: "node", node } : null);
    } else if (nextSelection?.kind === "edge") {
      const edge = visibleGraph.edges.find((candidate) => candidate.id === nextSelection.id) ?? null;
      onSelectionChange?.(edge ? { kind: "edge", edge } : null);
    } else {
      onSelectionChange?.(null);
    }
  }

  function selectNode(nodeId: string) {
    applySelection({ kind: "node", id: nodeId });
    const node = nodes.find((candidate) => candidate.id === nodeId);
    if (node) {
      setCenter(node.position.x + 140, node.position.y + 64, { zoom: 1.05, duration: 360 });
    }
  }

  function selectEdge(edgeId: string) {
    applySelection({ kind: "edge", id: edgeId });
  }

  function onSearch(value: string) {
    setQuery(value);
    const normalized = value.trim().toLowerCase();
    if (!normalized) {
      applySelection(null);
      return;
    }

    const matches = new Set(
      visibleGraph.nodes
        .filter((node) => `${node.label} ${node.type} ${Object.values(node.data).join(" ")}`.toLowerCase().includes(normalized))
        .map((node) => node.id)
    );
    const firstMatch = visibleGraph.nodes.find((node) => matches.has(node.id));
    applySelection(firstMatch ? { kind: "node", id: firstMatch.id } : null, matches);
    if (firstMatch) {
      window.setTimeout(() => fitView({ nodes: [{ id: firstMatch.id }], duration: 360, padding: 0.45 }), 0);
    }
  }

  function toggleType(type: GraphNodeType) {
    setEnabledTypes((current) => {
      const next = new Set(current);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next.size === 0 ? current : next;
    });
  }

  return (
    <div className={`grid min-h-[calc(100vh-112px)] gap-4 ${showDetailsPanel ? "xl:grid-cols-[1fr_380px]" : "grid-cols-1"}`}>
      <section className="overflow-hidden rounded-[6px] border border-[#2A3441] bg-[#121821]">
        <div className="flex flex-col gap-3 border-b border-[#2A3441] bg-[#171F2A]/45 p-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-base font-semibold text-[#E6E8EB]">Investigation Graph</h2>
            <p className="mt-1 text-xs text-[#9AA4AF]">{visibleGraph.nodes.length} nodes / {visibleGraph.edges.length} relationships</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="relative block">
              <span className="sr-only">Search graph nodes</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA4AF]" aria-hidden="true" />
              <input
                className="h-10 w-full rounded-[4px] border border-[#2A3441] bg-[#0B0F14] pl-9 pr-3 text-sm text-[#E6E8EB] outline-none placeholder:text-[#6f7a86] focus:border-[#C58B2A] sm:w-80"
                onChange={(event) => onSearch(event.target.value)}
                placeholder="Search graph nodes"
                type="search"
                value={query}
              />
            </label>
            <button
              className="inline-flex h-10 items-center justify-center gap-2 rounded-[4px] border border-[#2A3441] bg-[#121821] px-3 text-sm font-semibold text-[#E6E8EB] transition hover:border-[#C58B2A]"
              onClick={() => fitView({ duration: 420, padding: 0.24 })}
              type="button"
            >
              <Maximize2 className="h-4 w-4" aria-hidden="true" />
              Fit
            </button>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 border-b border-[#2A3441] bg-[#0B0F14] px-4 py-3">
          <div className="flex items-center gap-2 pr-2 text-xs font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">
            <Filter className="h-3.5 w-3.5" aria-hidden="true" />
            Filters
          </div>
          {filterTypes.map((type) => (
            <button
              className={`h-8 rounded-[4px] border px-2.5 text-xs font-semibold transition ${enabledTypes.has(type) ? "border-[#C58B2A] bg-[#1F1A12] text-[#F3D59A]" : "border-[#2A3441] bg-[#121821] text-[#9AA4AF]"}`}
              key={type}
              onClick={() => toggleType(type)}
              type="button"
            >
              {typeLabels[type]}
            </button>
          ))}
        </div>
        <div className="h-[720px]">
          <ReactFlow
            edges={edges}
            fitView
            fitViewOptions={{ padding: 0.22 }}
            minZoom={0.18}
            nodeTypes={nodeTypes}
            nodes={nodes}
            onEdgeClick={(_, edge) => selectEdge(edge.id)}
            onEdgesChange={onEdgesChange}
            onNodeClick={(_, node) => selectNode(node.id)}
            onNodesChange={onNodesChange}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#2A3441" gap={34} lineWidth={0.35} variant={BackgroundVariant.Lines} />
            <Controls position="bottom-left" />
            <MiniMap
              maskColor="rgba(11, 15, 20, 0.78)"
              nodeColor={(node) => nodeStyles[(node.data as unknown as FlowNodeData).graphNode.type]?.border ?? "#9AA4AF"}
              pannable
              position="bottom-right"
              zoomable
            />
          </ReactFlow>
        </div>
      </section>

      {showDetailsPanel ? (
        <aside className="rounded-[6px] border border-[#2A3441] bg-[#121821]">
          <div className="border-b border-[#2A3441] bg-[#171F2A]/45 px-4 py-3">
            <h2 className="text-base font-semibold text-[#E6E8EB]">Details</h2>
            <p className="mt-1 text-xs text-[#9AA4AF]">Overview, metadata, relationships, evidence, and statistics</p>
          </div>
          <AnimatePresence mode="wait">
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              className="p-4"
              exit={{ opacity: 0, y: 4 }}
              initial={{ opacity: 0, y: 4 }}
              key={selectedItem ? `${selectedItem.kind}-${selectedItem.id}` : "empty"}
              transition={{ duration: 0.14 }}
            >
              {selectedNode ? (
                <DetailsPanel badge={typeLabels[selectedNode.type]} graph={visibleGraph} itemId={selectedNode.id} nodeType={selectedNode.type} fields={selectedNode.data} label={selectedNode.label} />
              ) : selectedEdge ? (
                <DetailsPanel badge="Relationship" graph={visibleGraph} itemId={selectedEdge.id} fields={selectedEdge.data} label={selectedEdge.label} meta={`${selectedEdge.source} -> ${selectedEdge.target}`} />
              ) : (
                <div className="rounded-[4px] border border-dashed border-[#2A3441] p-5 text-sm text-[#9AA4AF]">
                  Select a node or relationship to inspect connected entities, metadata, evidence, and statistics.
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </aside>
      ) : null}
    </div>
  );
}

function InvestigationNode({ data }: NodeProps<Node<FlowNodeData>>) {
  const graphNode = data.graphNode;
  const style = nodeStyles[graphNode.type];
  const theme = nodeThemeClasses[graphNode.type];
  const Icon = nodeIcon(graphNode.type);
  const isEmphasized = data.selected || data.matched;
  const isConnected = data.connected;

  return (
    <motion.div
      animate={{ opacity: data.dimmed ? 0.35 : 1, scale: data.selected ? 1.03 : 1 }}
      transition={{ duration: 0.14 }}
    >
      <div
        className={`w-[280px] rounded-[6px] border p-3 shadow-[0_16px_40px_rgba(0,0,0,0.28)] ${theme.fill} ${isEmphasized ? "border-[#C58B2A] shadow-[0_0_0_2px_rgba(197,139,42,0.36),0_18px_48px_rgba(0,0,0,0.36)]" : isConnected ? theme.border : "border-[#2A3441]"}`}
      >
        <Handle className="!h-2 !w-2 !border-[#2A3441] !bg-[#C58B2A]" position={Position.Left} type="target" />
        <Handle className="!h-2 !w-2 !border-[#2A3441] !bg-[#C58B2A]" position={Position.Right} type="source" />
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${theme.accent}`} aria-hidden="true" />
          <span className={`text-[10px] font-semibold uppercase tracking-[0.14em] ${theme.accent}`}>
          {typeLabels[graphNode.type]}
          </span>
          {data.connected ? <Crosshair className="ml-auto h-3.5 w-3.5 text-[#C58B2A]" aria-hidden="true" /> : null}
        </div>
        <div className="mt-2 line-clamp-2 text-sm font-semibold leading-5 text-[#E6E8EB]">{graphNode.label}</div>
        <div className="mt-3 space-y-1 text-[11px] text-[#9AA4AF]">
          {renderNodeFacts(graphNode).map((fact) => (
            <div className="flex justify-between gap-3" key={fact.label}>
              <span>{fact.label}</span>
              <span className="max-w-[150px] truncate text-right tabular-nums text-[#C8CDD3]">{fact.value}</span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function DetailsPanel({
  badge,
  fields,
  graph,
  itemId,
  label,
  meta,
  nodeType
}: {
  badge: string;
  fields: Record<string, unknown>;
  graph: RelationshipGraph;
  itemId: string;
  label: string;
  meta?: string;
  nodeType?: GraphNodeType;
}) {
  const relationships = graph.edges.filter((edge) => edge.source === itemId || edge.target === itemId || edge.id === itemId);
  const relatedNodes = relationships
    .flatMap((edge) => [edge.source, edge.target])
    .filter((id) => id !== itemId)
    .map((id) => graph.nodes.find((node) => node.id === id))
    .filter((node): node is RelationshipGraphNode => Boolean(node));
  return (
    <div>
      <div className="inline-flex rounded-[4px] border border-[#C58B2A] bg-[#2A2115] px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.08em] text-[#F3D59A]">
        {badge}
      </div>
      <h3 className="mt-3 text-lg font-semibold text-[#E6E8EB]">{label}</h3>
      {meta ? <p className="mt-2 break-all text-xs text-[#9AA4AF]">{meta}</p> : null}

      <DetailSection title="Overview">
        <Field label="Summary" value={stringValue(fields.summary) || label} />
        <Field label="Relationships" value={String(relationships.length)} />
        {nodeType === "indicator" ? <Field label="Finding" value={stringValue(fields.finding) || "Not available"} /> : null}
      </DetailSection>

      <DetailSection title="Evidence">
        <Field label="Supporting evidence" value={stringValue(fields.supporting_evidence) || stringValue(fields.summary) || "No evidence payload attached"} />
        <Field label="Source" value={stringValue(fields.source) || "Not available"} />
        <Field label="Source URL" value={stringValue(fields.source_url) || "Not available"} />
      </DetailSection>

      <DetailSection title="Related Records">
        {relationships.length === 0 ? (
          <Field label="Connected records" value="None in current graph" />
        ) : (
          relationships.slice(0, 7).map((edge) => <Field key={edge.id} label={edge.label} value={`${edge.source} -> ${edge.target}`} />)
        )}
      </DetailSection>

      <DetailSection title="Related Companies">
        {relatedNodes.filter((node) => node.type === "company").length ? relatedNodes.filter((node) => node.type === "company").slice(0, 6).map((node) => <Field key={node.id} label={typeLabels[node.type]} value={node.label} />) : <Field label="Companies" value={stringValue(fields.related_company) || "None in current graph"} />}
      </DetailSection>

      <DetailSection title="Related Buyers">
        {relatedNodes.filter((node) => node.type === "buyer").length ? relatedNodes.filter((node) => node.type === "buyer").slice(0, 6).map((node) => <Field key={node.id} label={typeLabels[node.type]} value={node.label} />) : <Field label="Buyers" value={stringValue(fields.related_buyer) || "None in current graph"} />}
      </DetailSection>

      <DetailSection title="Related Awards">
        {relatedNodes.filter((node) => node.type === "award").length ? relatedNodes.filter((node) => node.type === "award").slice(0, 6).map((node) => <Field key={node.id} label={typeLabels[node.type]} value={node.label} />) : <Field label="Awards" value="None in current graph" />}
      </DetailSection>

      <DetailSection title="Documents">
        {arrayValues(fields.documents).length ? arrayValues(fields.documents).map((document) => <Field key={document} label="Document" value={document} />) : <Field label="Documents" value="None attached" />}
      </DetailSection>

      <DetailSection title="Timeline">
        {timelineValues(fields.timeline).length ? timelineValues(fields.timeline).map((item) => <Field key={`${item.label}-${item.date}`} label={item.label} value={item.date} />) : <Field label="Current graph" value={`${graph.nodes.length} nodes / ${graph.edges.length} edges`} />}
      </DetailSection>

      <DetailSection title="Source Explorer">
        <Field label="Source" value={stringValue(fields.source) || "Procurement records"} />
        <Field label="Node type" value={nodeType ? typeLabels[nodeType] : "Relationship"} />
      </DetailSection>

      <DetailSection title="Metadata">
        {Object.entries(fields).length === 0 ? <Field label="Metadata" value="Not available" /> : null}
        {Object.entries(fields).map(([key, value]) => (
          <Field key={key} label={key.replaceAll("_", " ")} value={displayValue(value)} />
        ))}
      </DetailSection>
    </div>
  );
}

function DetailSection({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="mt-5">
      <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-[#C58B2A]">{title}</h4>
      <div className="mt-3 divide-y divide-[#2A3441] rounded-[4px] border border-[#2A3441] bg-[#171F2A]">{children}</div>
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3">
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#9AA4AF]">{label}</div>
      <div className="mt-1 break-words text-sm text-[#E6E8EB]">{value}</div>
    </div>
  );
}

function toFlowNodes(graph: RelationshipGraph): Node<FlowNodeData>[] {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: "LR", ranksep: 150, nodesep: 70, marginx: 40, marginy: 40 });

  graph.nodes.forEach((node) => dagreGraph.setNode(node.id, { width: 280, height: 132 }));
  graph.edges.forEach((edge) => dagreGraph.setEdge(edge.source, edge.target));
  dagre.layout(dagreGraph);

  return graph.nodes.map((node) => {
    const position = dagreGraph.node(node.id) as { x: number; y: number };
    return {
      id: node.id,
      type: "investigation",
      data: { graphNode: node, selected: false, connected: false, dimmed: false, matched: false },
      position: { x: position.x - 140, y: position.y - 66 }
    };
  });
}

function toFlowEdges(graph: RelationshipGraph): Edge[] {
  return graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    animated: true,
    label: edge.label,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors[edge.type] },
    style: { stroke: edgeColors[edge.type], strokeWidth: edge.type.includes("indicator") ? 2.2 : 1.8 },
    labelStyle: { fill: "#C8CDD3", fontSize: 11, fontWeight: 600 },
    labelBgStyle: { fill: "#0B0F14", fillOpacity: 0.9 },
    type: "smoothstep"
  }));
}

function getConnectedNodeIds(graph: RelationshipGraph, selectedItem: SelectedItem): Set<string> {
  const connected = new Set<string>();
  if (!selectedItem) return connected;
  if (selectedItem.kind === "node") {
    connected.add(selectedItem.id);
    for (const edge of graph.edges) {
      if (edge.source === selectedItem.id) connected.add(edge.target);
      if (edge.target === selectedItem.id) connected.add(edge.source);
    }
    return connected;
  }
  const edge = graph.edges.find((candidate) => candidate.id === selectedItem.id);
  if (edge) {
    connected.add(edge.source);
    connected.add(edge.target);
  }
  return connected;
}

function applyNodeHighlights(nodes: Node<FlowNodeData>[], selectedNodeId: string | null, connectedNodeIds: Set<string>, matchingNodeIds: Set<string>): Node<FlowNodeData>[] {
  return nodes.map((node) => {
    const selected = selectedNodeId === node.id;
    const connected = connectedNodeIds.has(node.id);
    const matched = matchingNodeIds.has(node.id);
    return {
      ...node,
      data: {
        ...node.data,
        selected,
        connected,
        matched,
        dimmed: (connectedNodeIds.size > 0 && !connected) || (matchingNodeIds.size > 0 && !matched && !connected)
      }
    };
  });
}

function applyEdgeHighlights(edges: Edge[], graph: RelationshipGraph, selectedItem: SelectedItem): Edge[] {
  const connectedNodeIds = getConnectedNodeIds(graph, selectedItem);
  return edges.map((edge) => {
    const isSelectedEdge = selectedItem?.kind === "edge" && selectedItem.id === edge.id;
    const isConnected = connectedNodeIds.size === 0 || (connectedNodeIds.has(edge.source) && connectedNodeIds.has(edge.target));
    return {
      ...edge,
      animated: isConnected,
      style: {
        ...edge.style,
        opacity: isConnected ? 1 : 0.16,
        strokeWidth: isSelectedEdge ? 3.4 : isConnected ? 2 : 1.2
      }
    };
  });
}

function renderNodeFacts(node: RelationshipGraphNode): { label: string; value: string }[] {
  const data = node.data;
  if (node.type === "company") {
    return [
      { label: "Reg ID", value: String(data.registration_number ?? data.registration_id ?? "Not available") },
      { label: "Awards", value: String(data.award_count ?? data.total_awards ?? "0") }
    ];
  }
  if (node.type === "tender") {
    return [
      { label: "Value", value: String(data.estimated_value ?? data.value ?? "Not disclosed") },
      { label: "Published", value: String(data.published_date ?? data.publication_date ?? "No date") }
    ];
  }
  if (node.type === "award") {
    return [
      { label: "Amount", value: String(data.award_value ?? data.amount ?? "Not disclosed") },
      { label: "Date", value: String(data.award_date ?? data.date ?? "No date") }
    ];
  }
  if (node.type === "indicator") {
    return [
      { label: "Finding", value: String(data.title ?? node.label) },
      { label: "Source", value: String(data.source ?? "Procurement records") }
    ];
  }
  if (node.type === "evidence" || node.type === "web_evidence" || node.type === "document") {
    return [
      { label: "Source", value: String(data.source ?? "Stored evidence") },
      { label: "URL", value: String(data.source_url ?? "Not available") }
    ];
  }
  if (node.type === "category") {
    return [{ label: "Category", value: node.label }];
  }
  if (node.type === "organization") {
    return [{ label: "Organization", value: node.label }];
  }
  return [{ label: "Name", value: node.label }];
}

function filterGraphByType(graph: RelationshipGraph, enabledTypes: Set<GraphNodeType>): RelationshipGraph {
  const nodes = graph.nodes.filter((node) => enabledTypes.has(node.type));
  const nodeIds = new Set(nodes.map((node) => node.id));
  return {
    nodes,
    edges: graph.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  };
}

function nodeIcon(type: GraphNodeType) {
  if (type === "company") return Building2;
  if (type === "tender") return FileText;
  if (type === "award") return Award;
  if (type === "buyer") return UserRound;
  if (type === "indicator") return AlertTriangle;
  if (type === "evidence") return FileSearch;
  if (type === "document") return Archive;
  if (type === "web_evidence") return Globe2;
  if (type === "organization") return Landmark;
  return FolderTree;
}

function stringValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function arrayValues(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : [];
}

function timelineValues(value: unknown): Array<{ label: string; date: string }> {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const record = item as Record<string, unknown>;
      const label = stringValue(record.label);
      const date = stringValue(record.date);
      return label && date ? { label, date } : null;
    })
    .filter((item): item is { label: string; date: string } => item !== null);
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not available";
  if (Array.isArray(value)) return value.length ? value.map((item) => (typeof item === "object" ? JSON.stringify(item) : String(item))).join(", ") : "None";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
