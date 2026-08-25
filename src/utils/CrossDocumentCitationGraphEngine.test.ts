import { describe, it, expect } from 'vitest';
import {
  extractCitationsFromText,
  buildCitationGraph,
  detectCitationAnomalies,
} from './CrossDocumentCitationGraphEngine';

describe('CrossDocumentCitationGraphEngine', () => {
  const paperA = `In their landmark study, Smith et al. (2020) demonstrated deep learning advancements. Furthermore, Johnson and Lee (2021) expanded on these findings.`;
  const paperB = `Smith et al. (2020) provided foundational benchmarks for NLP. Additionally, Brown (2019) introduced key pre-training methodologies.`;

  it('should extract APA/IEEE citations correctly from text', () => {
    const citations = extractCitationsFromText(paperA);
    expect(citations).toBeDefined();
    expect(citations.length).toBe(2);
    expect(citations[0].rawText).toContain('Smith et al.');
    expect(citations[0].year).toBe(2020);
  });

  it('should build citation graph nodes and directed edges', () => {
    const documents = [
      { id: 'doc1', title: 'Paper 1', content: paperA },
      { id: 'doc2', title: 'Paper 2', content: paperB },
    ];

    const graph = buildCitationGraph(documents);

    expect(graph).toBeDefined();
    expect(graph.nodes.length).toBeGreaterThanOrEqual(2);
    expect(graph.edges.length).toBe(3); // 2 citations in paperA + 2 in paperB (Smith et al is shared)
  });

  it('should detect shared citation anomalies across documents', () => {
    const documents = [
      { id: 'doc1', title: 'Paper 1', content: paperA },
      { id: 'doc2', title: 'Paper 2', content: paperB },
    ];

    const graph = buildCitationGraph(documents);
    const anomalies = detectCitationAnomalies(graph, 1);

    expect(anomalies).toBeDefined();
    expect(anomalies.length).toBeGreaterThan(0);
    expect(anomalies[0].citationKey).toContain('smith');
  });
});
