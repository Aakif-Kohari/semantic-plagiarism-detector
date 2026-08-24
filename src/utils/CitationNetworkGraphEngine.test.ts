import { describe, it, expect, beforeEach } from 'vitest';
import { CitationNetworkGraphEngine } from './CitationNetworkGraphEngine';

describe('CitationNetworkGraphEngine', () => {
  let graph: CitationNetworkGraphEngine;

  beforeEach(() => {
    graph = new CitationNetworkGraphEngine();
    graph.addNode({ id: 'P1', title: 'Paper 1', author: 'Author A', year: 2020 });
    graph.addNode({ id: 'P2', title: 'Paper 2', author: 'Author B', year: 2021 });
    graph.addNode({ id: 'P3', title: 'Paper 3', author: 'Author C', year: 2022 });
  });

  it('should compute PageRank centrality scores correctly', () => {
    graph.addEdge({ sourceId: 'P1', targetId: 'P2', weight: 1.0 });
    graph.addEdge({ sourceId: 'P3', targetId: 'P2', weight: 1.0 });

    const ranks = graph.computePageRank();
    expect(ranks.length).toBe(3);
    expect(ranks[0].nodeId).toBe('P2');
    expect(ranks[0].rank).toBe(1);
  });

  it('should detect circular citation loops', () => {
    graph.addEdge({ sourceId: 'P1', targetId: 'P2', weight: 1.0 });
    graph.addEdge({ sourceId: 'P2', targetId: 'P3', weight: 1.0 });
    graph.addEdge({ sourceId: 'P3', targetId: 'P1', weight: 1.0 });

    const cycles = graph.detectCircularCitations();
    expect(cycles.length).toBeGreaterThan(0);
    expect(cycles[0].length).toBe(3);
  });

  it('should calculate graph telemetry and density', () => {
    graph.addEdge({ sourceId: 'P1', targetId: 'P2', weight: 1.0 });
    const telemetry = graph.getGraphTelemetry();
    expect(telemetry.nodeCount).toBe(3);
    expect(telemetry.edgeCount).toBe(1);
    expect(telemetry.density).toBeGreaterThan(0);
  });
});
