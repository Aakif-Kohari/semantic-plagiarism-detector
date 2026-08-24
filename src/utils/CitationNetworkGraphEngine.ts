/**
 * Citation Network Graph & PageRank Circular Reference Detection Engine.
 * Constructs directed citation graphs, calculates PageRank centralities,
 * detects circular citation loops, and computes graph density telemetry.
 */

export interface CitationNode {
  id: string;
  title: string;
  author: string;
  year: number;
}

export interface CitationEdge {
  sourceId: string;
  targetId: string;
  weight: number;
}

export interface PageRankResult {
  nodeId: string;
  score: number;
  rank: number;
}

export interface CircularCitationCycle {
  cycle: string[];
  length: number;
}

export class CitationNetworkGraphEngine {
  private nodes: Map<string, CitationNode>;
  private adjacencyList: Map<string, Map<string, number>>;
  private inEdges: Map<string, Map<string, number>>;

  constructor() {
    this.nodes = new Map();
    this.adjacencyList = new Map();
    this.inEdges = new Map();
  }

  public addNode(node: CitationNode): void {
    if (!this.nodes.has(node.id)) {
      this.nodes.set(node.id, node);
      this.adjacencyList.set(node.id, new Map());
      this.inEdges.set(node.id, new Map());
    }
  }

  public addEdge(edge: CitationEdge): void {
    if (!this.nodes.has(edge.sourceId) || !this.nodes.has(edge.targetId)) {
      throw new Error(`Nodes ${edge.sourceId} and ${edge.targetId} must be registered before creating an edge.`);
    }

    this.adjacencyList.get(edge.sourceId)!.set(edge.targetId, edge.weight);
    this.inEdges.get(edge.targetId)!.set(edge.sourceId, edge.weight);
  }

  public computePageRank(dampingFactor: number = 0.85, maxIterations: number = 100, tolerance: number = 1e-6): PageRankResult[] {
    const nodeIds = Array.from(this.nodes.keys());
    const N = nodeIds.length;
    if (N === 0) return [];

    let ranks = new Map<string, number>();
    const initialRank = 1.0 / N;
    nodeIds.forEach(id => ranks.set(id, initialRank));

    for (let iter = 0; iter < maxIterations; iter++) {
      const nextRanks = new Map<string, number>();
      let diff = 0;

      for (const nodeId of nodeIds) {
        let incomingSum = 0;
        const incomingMap = this.inEdges.get(nodeId) || new Map();

        incomingMap.forEach((_, sourceId) => {
          const outDegree = (this.adjacencyList.get(sourceId) || new Map()).size;
          if (outDegree > 0) {
            incomingSum += (ranks.get(sourceId) || 0) / outDegree;
          }
        });

        const newRank = (1 - dampingFactor) / N + dampingFactor * incomingSum;
        nextRanks.set(nodeId, newRank);
        diff += Math.abs(newRank - (ranks.get(nodeId) || 0));
      }

      ranks = nextRanks;
      if (diff < tolerance) break;
    }

    const sortedResults = Array.from(ranks.entries())
      .map(([nodeId, score]) => ({ nodeId, score, rank: 0 }))
      .sort((a, b) => b.score - a.score);

    sortedResults.forEach((res, idx) => {
      res.rank = idx + 1;
    });

    return sortedResults;
  }

  public detectCircularCitations(): CircularCitationCycle[] {
    const cycles: CircularCitationCycle[] = [];
    const visited = new Set<string>();
    const recursionStack = new Set<string>();
    const path: string[] = [];

    const dfs = (currentNode: string) => {
      visited.add(currentNode);
      recursionStack.add(currentNode);
      path.push(currentNode);

      const neighbors = this.adjacencyList.get(currentNode) || new Map();
      neighbors.forEach((_, neighborId) => {
        if (!visited.has(neighborId)) {
          dfs(neighborId);
        } else if (recursionStack.has(neighborId)) {
          const cycleStartIndex = path.indexOf(neighborId);
          if (cycleStartIndex !== -1) {
            const cyclePath = path.slice(cycleStartIndex);
            cyclePath.push(neighborId);
            cycles.push({
              cycle: cyclePath,
              length: cyclePath.length - 1
            });
          }
        }
      });

      path.pop();
      recursionStack.delete(currentNode);
    };

    this.nodes.forEach((_, nodeId) => {
      if (!visited.has(nodeId)) {
        dfs(nodeId);
      }
    });

    return cycles;
  }

  public getGraphTelemetry(): { nodeCount: number; edgeCount: number; density: number } {
    const nodeCount = this.nodes.size;
    let edgeCount = 0;
    this.adjacencyList.forEach(neighbors => {
      edgeCount += neighbors.size;
    });

    const maxEdges = nodeCount * (nodeCount - 1);
    const density = maxEdges > 0 ? edgeCount / maxEdges : 0;

    return {
      nodeCount,
      edgeCount,
      density: Math.round(density * 10000) / 10000
    };
  }
}
