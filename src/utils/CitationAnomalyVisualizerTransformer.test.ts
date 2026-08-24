import { describe, it, expect } from 'vitest';
import { CitationAnomalyVisualizerTransformer } from './CitationAnomalyVisualizerTransformer';

describe('CitationAnomalyVisualizerTransformer', () => {
  it('should transform graph analysis data into D3 visual payload', () => {
    const ranks = [{ nodeId: 'P1', score: 0.8, rank: 1 }];
    const cycles = [{ cycle: ['P1', 'P2', 'P1'], length: 2 }];

    const d3Data = CitationAnomalyVisualizerTransformer.transformToD3Graph(ranks, cycles);
    expect(d3Data.nodes.length).toBe(1);
    expect(d3Data.links.length).toBe(2);
    expect(d3Data.nodes[0].color).toBe('#ef4444');
  });
});
