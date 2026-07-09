"use client";

import dagre from "dagre";
import {
  Background,
  BackgroundVariant,
  Controls,
  Edge,
  EdgeTypes,
  Handle,
  MarkerType,
  MiniMap,
  Node,
  NodeProps,
  PanOnScrollMode,
  Position,
  ReactFlow,
  ReactFlowProvider,
  SmoothStepEdge,
  useEdgesState,
  useNodesState,
  useReactFlow
} from "@xyflow/react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Archive, Award, Building2, Crosshair, Eye, EyeOff, FileSearch, FileText, Filter, FolderTree, Globe2, Landmark, Maximize2, RotateCcw, Search, UserRound, X } from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { GraphEdgeType, GraphNodeType, RelationshipGraph, RelationshipGraphNode } from "@/lib/api";

type SelectedItem = { kind: "node"; id: string } | { kind: "edge"; id: string } | null;
type LayoutMode = "LR" | "TB";

type FlowNodeData = {
  graphNode: RelationshipGraphNode;
  selected: boolean;
  connected: boolean;
  dimmed: boolean;
  layoutMode: LayoutMode;
  matched: boolean;
};

type RelationshipGraphExplorerProps = {
  graph: RelationshipGraph;
  compact?: boolean;
  fullscreen?: boolean;
  height?: number | string;
  onExitFullscreen?: () => void;
  subtitle?: string;
  title?: string;
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
  company: { border: "#3B6FE0", fill: "#101a2c", accent: "#7fa6f0" },
  tender: { border: "#b8842a", fill: "#231c0e", accent: "#f0b429" },
  award: { border: "#2e8b63", fill: "#0e1e18", accent: "#43c08a" },
  buyer: { border: "#2a8c86", fill: "#0c1e1d", accent: "#4fd1c5" },
  indicator: { border: "#c0392b", fill: "#241012", accent: "#ef4d54" },
  evidence: { border: "#46566b", fill: "#141b26", accent: "#93a1b5" },
  document: { border: "#46566b", fill: "#141b26", accent: "#93a1b5" },
  web_evidence: { border: "#46566b", fill: "#141b26", accent: "#93a1b5" },
  organization: { border: "#7c5cd0", fill: "#171426", accent: "#b79cf0" },
  category: { border: "#b8842a", fill: "#231c0e", accent: "#f0b429" }
};

const HL = "#e0a73e"; // gold highlight for selection/search

const edgeColors: Record<GraphEdgeType, string> = {
  company_tender: "#46566b",
  tender_award: "#5b6f4a",
  award_company: "#46566b",
  buyer_tender: "#3f5560",
  buyer_company: "#3f5560",
  tender_indicator: "#7a3a3a",
  company_indicator: "#7a3a3a",
  evidence_indicator: "#7a3a3a",
  tender_evidence: "#3a4453",
  web_evidence_company: "#3a4453",
  web_evidence_tender: "#3a4453",
  web_evidence_award: "#3a4453",
  document_tender: "#3a4453",
  category_tender: "#3a4453",
  organization_evidence: "#3a4453"
};

const filterTypes: GraphNodeType[] = ["company", "buyer", "tender", "award", "indicator", "evidence", "document", "web_evidence", "organization", "category"];

const nodeTypes = {
  investigation: InvestigationNode
};

const edgeTypes: EdgeTypes = {
  smoothstep: SmoothStepEdge
};

export function RelationshipGraphExplorer({
  graph,
  compact = false,
  fullscreen = false,
  height,
  onExitFullscreen,
  subtitle,
  title = "Investigation Graph"
}: RelationshipGraphExplorerProps) {
  return (
    <ReactFlowProvider>
      <RelationshipGraphCanvas
        compact={compact}
        fullscreen={fullscreen}
        graph={graph}
        height={height}
        onExitFullscreen={onExitFullscreen}
        subtitle={subtitle}
        title={title}
      />
    </ReactFlowProvider>
  );
}

function RelationshipGraphCanvas({
  compact,
  fullscreen,
  graph,
  height,
  onExitFullscreen,
  subtitle,
  title
}: Required<Pick<RelationshipGraphExplorerProps, "compact" | "fullscreen" | "graph" | "title">> &
  Pick<RelationshipGraphExplorerProps, "height" | "onExitFullscreen" | "subtitle">) {
  const [enabledTypes, setEnabledTypes] = useState<Set<GraphNodeType>>(() => new Set(filterTypes));
  const [collapsedTypes, setCollapsedTypes] = useState<Set<GraphNodeType>>(() => new Set());
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("LR");
  const visibleGraph = useMemo(() => filterGraphByType(graph, enabledTypes, collapsedTypes), [collapsedTypes, enabledTypes, graph]);
  const initialNodes = useMemo(() => toFlowNodes(visibleGraph, layoutMode, fullscreen), [fullscreen, visibleGraph, layoutMode]);
  const initialEdges = useMemo(() => toFlowEdges(visibleGraph), [visibleGraph]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedItem, setSelectedItem] = useState<SelectedItem>(null);
  const [query, setQuery] = useState("");
  const { fitView, getZoom, setCenter } = useReactFlow();
  const nodeCounts = useMemo(() => countNodeTypes(graph.nodes), [graph.nodes]);
  const visibleCounts = useMemo(() => countNodeTypes(visibleGraph.nodes), [visibleGraph.nodes]);
  const indicatorCount = visibleCounts.indicator ?? 0;
  const largeGraph = graph.nodes.length > 80;
  const fitPadding = fullscreen ? (largeGraph ? 0.08 : 0.16) : compact ? 0.18 : 0.28;

  const selectedNode = selectedItem?.kind === "node" ? visibleGraph.nodes.find((node) => node.id === selectedItem.id) : null;
  const selectedEdge = selectedItem?.kind === "edge" ? visibleGraph.edges.find((edge) => edge.id === selectedItem.id) : null;

  const fitGraph = useCallback((duration = 420) => {
    window.requestAnimationFrame(() => {
      fitView({ duration, padding: fitPadding, includeHiddenNodes: false });
    });
  }, [fitPadding, fitView]);

  function applySelection(nextSelection: SelectedItem, matches = new Set<string>()) {
    setSelectedItem(nextSelection);
    const connectedNodeIds = getConnectedNodeIds(visibleGraph, nextSelection);
    setNodes((current) => applyNodeHighlights(current, nextSelection?.kind === "node" ? nextSelection.id : null, connectedNodeIds, matches));
    setEdges((current) => applyEdgeHighlights(current, visibleGraph, nextSelection));
  }

  function selectNode(nodeId: string) {
    applySelection({ kind: "node", id: nodeId });
    const node = nodes.find((candidate) => candidate.id === nodeId);
    if (node) {
      const zoom = Math.min(Math.max(getZoom(), fullscreen ? 0.65 : 0.8), fullscreen ? 1.15 : 1.05);
      setCenter(node.position.x + 150, node.position.y + 66, { zoom, duration: 360 });
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
      window.requestAnimationFrame(() => fitView({ nodes: [{ id: firstMatch.id }], duration: 360, padding: 0.45 }));
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

  const centerGraph = useCallback(() => {
    if (nodes.length === 0) return;
    const bounds = nodes.reduce(
      (acc, node) => {
        const width = 300;
        const height = 132;
        return {
          minX: Math.min(acc.minX, node.position.x),
          minY: Math.min(acc.minY, node.position.y),
          maxX: Math.max(acc.maxX, node.position.x + width),
          maxY: Math.max(acc.maxY, node.position.y + height)
        };
      },
      { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity }
    );
    const zoom = Math.min(Math.max(getZoom(), fullscreen ? 0.25 : 0.45), fullscreen ? 1.05 : 1);
    setCenter((bounds.minX + bounds.maxX) / 2, (bounds.minY + bounds.maxY) / 2, { zoom, duration: 360 });
  }, [fullscreen, getZoom, nodes, setCenter]);

  const resetView = useCallback(() => {
    setQuery("");
    applySelection(null);
    fitGraph(420);
  }, [fitGraph]);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    setSelectedItem(null);
    fitGraph(520);
  }, [fitGraph, initialEdges, initialNodes, setEdges, setNodes]);

  useEffect(() => {
    if (!fullscreen) return;

    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const isTextInput =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        Boolean(target?.isContentEditable);
      if (isTextInput) return;

      if (event.key === "Escape") {
        event.preventDefault();
        onExitFullscreen?.();
        return;
      }
      if (event.key.toLowerCase() === "f") {
        event.preventDefault();
        fitGraph(360);
        return;
      }
      if (event.key.toLowerCase() === "r") {
        event.preventDefault();
        resetView();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [fitGraph, fullscreen, onExitFullscreen, resetView]);

  function toggleCluster(type: GraphNodeType) {
    setCollapsedTypes((current) => {
      const next = new Set(current);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  return (
    <div className={
      fullscreen
        ? "grid h-dvh w-dvw min-h-0 min-w-0 overflow-hidden bg-bg xl:grid-cols-[minmax(0,1fr)_380px]"
        : `grid gap-4 ${compact ? "min-h-0 xl:grid-cols-[1fr_340px]" : "min-h-[calc(100vh-112px)] xl:grid-cols-[1fr_380px]"}`
    }>
      <section className={
        fullscreen
          ? "flex min-h-0 min-w-0 flex-col overflow-hidden border-r border-border bg-bg"
          : "overflow-hidden rounded-[16px] border border-border bg-surface shadow-[0_24px_48px_-24px_rgba(0,0,0,0.7)]"
      }>
        <div className="flex shrink-0 flex-col gap-3 border-b border-border bg-bg-2/40 p-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-base font-semibold text-text">{title}</h2>
            {subtitle ? <p className="mt-1 max-w-2xl truncate text-xs text-faint">{subtitle}</p> : null}
            <div className="mt-2 flex flex-wrap gap-1.5">
              <GraphStat label="Nodes" value={visibleGraph.nodes.length} />
              <GraphStat label="Relationships" value={visibleGraph.edges.length} />
              <GraphStat label="Indicators" value={indicatorCount} tone={indicatorCount > 0 ? "danger" : "neutral"} />
            </div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="relative block">
              <span className="sr-only">Search graph nodes</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
              <input
                className="h-10 w-full rounded-[12px] border border-border bg-bg pl-9 pr-3 text-sm text-text outline-none placeholder:text-faint focus:border-accent/60 sm:w-80"
                onChange={(event) => onSearch(event.target.value)}
                placeholder="Search graph nodes"
                type="search"
                value={query}
              />
            </label>
            <div className="inline-flex h-10 rounded-[12px] border border-border bg-bg p-0.5" aria-label="Graph layout">
              {(["LR", "TB"] as LayoutMode[]).map((mode) => (
                <button
                  aria-pressed={layoutMode === mode}
                  className={`rounded-[9px] px-3 text-xs font-semibold transition ${
                    layoutMode === mode ? "bg-accent/15 text-accent" : "text-muted hover:text-text"
                  }`}
                  key={mode}
                  onClick={() => setLayoutMode(mode)}
                  type="button"
                >
                  {mode === "LR" ? "Horizontal" : "Vertical"}
                </button>
              ))}
            </div>
            <button
              className="inline-flex h-10 items-center justify-center gap-2 rounded-[12px] border border-border bg-surface px-3 text-sm font-semibold text-text transition hover:border-accent/50 hover:text-accent"
              onClick={() => fitGraph(420)}
              type="button"
            >
              <Maximize2 className="h-4 w-4" aria-hidden="true" />
              Fit Graph
            </button>
            <button
              className="inline-flex h-10 items-center justify-center gap-2 rounded-[12px] border border-border bg-surface px-3 text-sm font-semibold text-muted transition hover:border-accent/50 hover:text-accent"
              onClick={centerGraph}
              type="button"
            >
              <Crosshair className="h-4 w-4" aria-hidden="true" />
              Center Graph
            </button>
            <button
              className="inline-flex h-10 items-center justify-center gap-2 rounded-[12px] border border-border bg-surface px-3 text-sm font-semibold text-muted transition hover:border-accent/50 hover:text-accent"
              onClick={resetView}
              type="button"
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Reset Camera
            </button>
            {fullscreen && onExitFullscreen ? (
              <button
                aria-label="Exit full graph"
                className="grid h-10 w-10 place-items-center rounded-[12px] border border-border bg-surface text-muted transition hover:border-border-strong hover:text-text"
                onClick={onExitFullscreen}
                title="Exit full graph"
                type="button"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            ) : null}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 border-b border-border bg-bg-2/20 px-4 py-3">
          <div className="flex items-center gap-2 pr-2 text-xs font-semibold uppercase tracking-[0.12em] text-faint">
            <Filter className="h-3.5 w-3.5" aria-hidden="true" />
            Filters
          </div>
          {filterTypes.map((type) => (
            <button
              className={`h-8 rounded-[10px] border px-2.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${enabledTypes.has(type) ? "border-accent/50 bg-accent/10 text-accent" : "border-border bg-surface text-muted hover:text-text"}`}
              disabled={!nodeCounts[type]}
              key={type}
              onClick={() => toggleType(type)}
              type="button"
            >
              {typeLabels[type]} <span className="ml-1 tabular text-faint">{nodeCounts[type] ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 border-b border-border bg-bg-2/10 px-4 py-3">
          <div className="flex items-center gap-2 pr-2 text-xs font-semibold uppercase tracking-[0.12em] text-faint">
            Clusters
          </div>
          {filterTypes.filter((type) => (nodeCounts[type] ?? 0) > 0).map((type) => (
            <button
              className={`inline-flex h-8 items-center gap-1.5 rounded-[10px] border px-2.5 text-xs font-semibold transition ${
                collapsedTypes.has(type) ? "border-warning/40 bg-warning/10 text-warning" : "border-border bg-surface text-muted hover:text-text"
              }`}
              key={type}
              onClick={() => toggleCluster(type)}
              type="button"
            >
              {collapsedTypes.has(type) ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              {typeLabels[type]}
            </button>
          ))}
        </div>
        {largeGraph && (
          <div className="shrink-0 border-b border-border bg-warning/[0.04] px-4 py-2 text-xs text-muted">
            Large graph mode active. Use cluster controls and search to narrow the investigation view.
          </div>
        )}
        <div className={`${fullscreen ? "min-h-0 flex-1" : ""} bg-bg`} style={fullscreen ? undefined : { height: height ?? (compact ? 640 : 720) }}>
          <ReactFlow
            edges={edges}
            edgeTypes={edgeTypes}
            fitView
            fitViewOptions={{ padding: fitPadding, includeHiddenNodes: false }}
            maxZoom={fullscreen ? 2.4 : 1.6}
            minZoom={fullscreen ? 0.01 : 0.04}
            nodeTypes={nodeTypes}
            nodes={nodes}
            onEdgeClick={(_, edge) => selectEdge(edge.id)}
            onEdgesChange={onEdgesChange}
            onNodeClick={(_, node) => selectNode(node.id)}
            onNodesChange={onNodesChange}
            onlyRenderVisibleElements={largeGraph}
            panOnDrag
            panOnScroll={false}
            panOnScrollMode={PanOnScrollMode.Free}
            panOnScrollSpeed={0.85}
            paneClickDistance={4}
            preventScrolling
            proOptions={{ hideAttribution: true }}
            selectionOnDrag
            selectNodesOnDrag={false}
            style={{ height: "100%", width: "100%" }}
            zoomOnDoubleClick={false}
            zoomOnPinch
            zoomOnScroll
          >
            <Background color="#1c2634" gap={34} lineWidth={0.4} variant={BackgroundVariant.Lines} />
            <Controls fitViewOptions={{ padding: fitPadding }} position="bottom-left" />
            <MiniMap
              className="!bg-bg-2/90"
              maskColor="rgba(8, 11, 17, 0.82)"
              nodeColor={(node) => nodeStyles[(node.data as unknown as FlowNodeData).graphNode.type]?.border ?? "#46566b"}
              pannable
              position="bottom-right"
              zoomable
            />
          </ReactFlow>
        </div>
      </section>

      <aside className={
        fullscreen
          ? "hidden min-h-0 overflow-y-auto bg-surface xl:block"
          : `rounded-[16px] border border-border bg-surface shadow-[0_24px_48px_-24px_rgba(0,0,0,0.7)] ${compact ? "max-xl:hidden" : ""}`
      }>
        <div className="sticky top-0 z-10 border-b border-border bg-bg-2/95 px-4 py-3 backdrop-blur">
          <h2 className="text-base font-semibold text-text">Details</h2>
          <p className="mt-1 text-xs text-muted">Overview, metadata, relationships, evidence, and statistics</p>
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
              <div className="rounded-[14px] border border-dashed border-border bg-bg-2/30 p-5 text-sm text-muted">
                Select a node or relationship to inspect connected entities, metadata, evidence, and statistics.
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </aside>
    </div>
  );
}

function InvestigationNode({ data }: NodeProps<Node<FlowNodeData>>) {
  const graphNode = data.graphNode;
  const style = nodeStyles[graphNode.type];
  const Icon = nodeIcon(graphNode.type);
  const targetPosition = data.layoutMode === "TB" ? Position.Top : Position.Left;
  const sourcePosition = data.layoutMode === "TB" ? Position.Bottom : Position.Right;

  return (
    <motion.div
      animate={{ opacity: data.dimmed ? 0.35 : 1, scale: data.selected ? 1.03 : 1 }}
      transition={{ duration: 0.14 }}
    >
      <div
        className="rounded-[14px] border p-3"
        style={{
          backgroundColor: style.fill,
          borderColor: data.selected || data.matched ? HL : data.connected ? style.border : "#212c3b",
          boxShadow: data.selected || data.matched
            ? `0 0 0 2px rgba(224,167,62,0.35), 0 18px 48px rgba(0,0,0,0.6)`
            : "0 12px 32px -16px rgba(0,0,0,0.7)",
          width: 300
        }}
      >
        <Handle className="!h-2 !w-2 !border-0 !bg-[#e0a73e]" position={targetPosition} type="target" />
        <Handle className="!h-2 !w-2 !border-0 !bg-[#e0a73e]" position={sourcePosition} type="source" />
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4" style={{ color: style.accent }} aria-hidden="true" />
          <span className="text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ color: style.accent }}>
          {typeLabels[graphNode.type]}
          </span>
          {data.connected ? <Crosshair className="ml-auto h-3.5 w-3.5" style={{ color: HL }} aria-hidden="true" /> : null}
        </div>
        <div className="mt-2 line-clamp-2 text-sm font-semibold leading-5 text-[#e7ecf3]">{graphNode.label}</div>
        <div className="mt-3 space-y-1 text-[11px] text-[#93a1b5]">
          {renderNodeFacts(graphNode).map((fact) => (
            <div className="flex justify-between gap-3" key={fact.label}>
              <span>{fact.label}</span>
              <span className="max-w-[170px] truncate text-right tabular-nums text-[#c3ccd8]">{fact.value}</span>
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
  const relatedCompanies = relatedNodes.filter((node) => node.type === "company");
  const relatedBuyers = relatedNodes.filter((node) => node.type === "buyer");
  const relatedAwards = relatedNodes.filter((node) => node.type === "award");
  return (
    <div>
      <div className="inline-flex rounded-[10px] border border-accent/30 bg-accent/10 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.08em] text-accent">
        {badge}
      </div>
      <h3 className="mt-3 text-lg font-semibold text-text">{label}</h3>
      {meta ? <p className="mt-2 break-all font-mono text-xs text-faint">{meta}</p> : null}

      <div className="mt-4 grid grid-cols-3 gap-2">
        <GraphStat label="Links" value={relationships.length} />
        <GraphStat label="Companies" value={relatedCompanies.length} />
        <GraphStat label="Buyers" value={relatedBuyers.length} />
      </div>

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
        {relatedCompanies.length ? relatedCompanies.slice(0, 6).map((node) => <Field key={node.id} label={typeLabels[node.type]} value={node.label} />) : <Field label="Companies" value={stringValue(fields.related_company) || "None in current graph"} />}
      </DetailSection>

      <DetailSection title="Related Buyers">
        {relatedBuyers.length ? relatedBuyers.slice(0, 6).map((node) => <Field key={node.id} label={typeLabels[node.type]} value={node.label} />) : <Field label="Buyers" value={stringValue(fields.related_buyer) || "None in current graph"} />}
      </DetailSection>

      <DetailSection title="Related Awards">
        {relatedAwards.length ? relatedAwards.slice(0, 6).map((node) => <Field key={node.id} label={typeLabels[node.type]} value={node.label} />) : <Field label="Awards" value="None in current graph" />}
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

function GraphStat({
  label,
  value,
  tone = "neutral"
}: {
  label: string;
  value: number;
  tone?: "neutral" | "danger";
}) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium ${
      tone === "danger" ? "border-danger/30 bg-danger/10 text-danger" : "border-border bg-bg-2/50 text-muted"
    }`}>
      <span className="tabular font-semibold text-text">{value}</span>
      {label}
    </span>
  );
}

function DetailSection({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="mt-5">
      <h4 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-accent">{title}</h4>
      <div className="mt-2 divide-y divide-border rounded-[12px] border border-border bg-bg-2/30">{children}</div>
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">{label}</div>
      <div className="mt-1 break-words text-sm text-text">{value}</div>
    </div>
  );
}

function toFlowNodes(graph: RelationshipGraph, rankdir: LayoutMode, fullscreen = false): Node<FlowNodeData>[] {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  const large = graph.nodes.length > 80;
  const huge = graph.nodes.length > 220;
  dagreGraph.setGraph({
    rankdir,
    ranksep: rankdir === "LR" ? (huge ? 360 : large ? 280 : 190) : (huge ? 230 : large ? 180 : 128),
    nodesep: rankdir === "LR" ? (huge ? 180 : large ? 132 : 88) : (huge ? 170 : large ? 136 : 104),
    edgesep: large ? 48 : 28,
    marginx: fullscreen ? 180 : 96,
    marginy: fullscreen ? 180 : 96
  });

  graph.nodes.forEach((node) => dagreGraph.setNode(node.id, { width: 300, height: 132 }));
  graph.edges.forEach((edge) => dagreGraph.setEdge(edge.source, edge.target, { weight: edge.type.includes("indicator") ? 2 : 1 }));
  dagre.layout(dagreGraph);

  return graph.nodes.map((node) => {
    const position = dagreGraph.node(node.id) as { x: number; y: number };
    return {
      id: node.id,
      type: "investigation",
      data: { graphNode: node, selected: false, connected: false, dimmed: false, layoutMode: rankdir, matched: false },
      position: { x: position.x - 150, y: position.y - 66 }
    };
  });
}

function toFlowEdges(graph: RelationshipGraph): Edge[] {
  const large = graph.nodes.length > 80;
  return graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    data: { graphType: edge.type },
    animated: true,
    label: edge.label,
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors[edge.type] },
    style: { stroke: edgeColors[edge.type], strokeWidth: edge.type.includes("indicator") ? 2.2 : 1.45, opacity: large ? 0.82 : 1 },
    labelStyle: { fill: "#93a1b5", fontSize: large ? 10 : 11, fontWeight: 600 },
    labelBgStyle: { fill: "#111823", fillOpacity: 0.92 },
    labelBgPadding: [6, 3] as [number, number],
    labelBgBorderRadius: 6,
    pathOptions: { borderRadius: large ? 22 : 14, offset: large ? 42 : 28 },
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
    const active = isSelectedEdge || (selectedItem !== null && isConnected);
    const graphType = (edge.data as { graphType?: GraphEdgeType } | undefined)?.graphType;
    const baseStroke = graphType ? edgeColors[graphType] : (edge.style as { stroke?: string } | undefined)?.stroke;
    return {
      ...edge,
      animated: isConnected,
      style: {
        ...edge.style,
        stroke: active ? HL : baseStroke,
        opacity: isConnected ? 1 : 0.14,
        strokeWidth: isSelectedEdge ? 3.2 : isConnected ? 2 : 1.1
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

function filterGraphByType(graph: RelationshipGraph, enabledTypes: Set<GraphNodeType>, collapsedTypes: Set<GraphNodeType>): RelationshipGraph {
  const nodes = graph.nodes.filter((node) => enabledTypes.has(node.type) && !collapsedTypes.has(node.type));
  const nodeIds = new Set(nodes.map((node) => node.id));
  return {
    nodes,
    edges: graph.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  };
}

function countNodeTypes(nodes: RelationshipGraphNode[]): Partial<Record<GraphNodeType, number>> {
  return nodes.reduce<Partial<Record<GraphNodeType, number>>>((counts, node) => {
    counts[node.type] = (counts[node.type] ?? 0) + 1;
    return counts;
  }, {});
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
