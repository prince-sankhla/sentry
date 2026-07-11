declare module "dagre" {
  type GraphLabel = {
    rankdir?: string;
    ranksep?: number;
    nodesep?: number;
    edgesep?: number;
    marginx?: number;
    marginy?: number;
  };

  type EdgeLabel = {
    weight?: number;
    minlen?: number;
  };

  type NodeLabel = {
    width: number;
    height: number;
    x?: number;
    y?: number;
  };

  class Graph {
    setDefaultEdgeLabel(callback: () => Record<string, unknown>): void;
    setGraph(label: GraphLabel): void;
    setNode(id: string, label: NodeLabel): void;
    setEdge(source: string, target: string, label?: EdgeLabel): void;
    node(id: string): NodeLabel;
  }

  const dagre: {
    graphlib: {
      Graph: typeof Graph;
    };
    layout(graph: Graph): void;
  };

  export default dagre;
}
