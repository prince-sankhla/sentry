declare module "dagre" {
  type GraphLabel = {
    rankdir?: string;
    ranksep?: number;
    nodesep?: number;
    marginx?: number;
    marginy?: number;
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
    setEdge(source: string, target: string): void;
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
