/**
 * Citation Anomaly Visualizer Data Transformer.
 * Prepares network graph nodes and links into D3 / ECharts compatible format.
 */

import { PageRankResult, CircularCitationCycle } from './CitationNetworkGraphEngine';

export interface GraphVisualizationNode {
  id: string;
  label: string;
  val: number;
  color: string;
}

export interface GraphVisualizationLink {
  source: string;
  target: string;
  curvature: number;
}

export class CitationAnomalyVisualizerTransformer {
  public static transformToD3Graph(
    ranks: PageRankResult[],
    cycles: CircularCitationCycle[]
  ): { nodes: GraphVisualizationNode[]; links: GraphVisualizationLink[] } {
    const cycleNodeIds = new Set<string>();
    cycles.forEach(c => c.cycle.forEach(id => cycleNodeIds.add(id)));

    const nodes: GraphVisualizationNode[] = ranks.map(r => ({
      id: r.nodeId,
      label: `Paper ${r.nodeId} (Rank #${r.rank})`,
      val: Math.max(5, Math.round(r.score * 100)),
      color: cycleNodeIds.has(r.nodeId) ? '#ef4444' : '#3b82f6'
    }));

    const links: GraphVisualizationLink[] = [];
    cycles.forEach(c => {
      for (let i = 0; i < c.cycle.length - 1; i++) {
        links.push({
          source: c.cycle[i],
          target: c.cycle[i + 1],
          curvature: 0.2
        });
      }
    });

    return { nodes, links };
  }
}
