/**
 * Cross-Document Citation Graph Engine
 * Extracts citations (APA, IEEE, Vancouver formats) from academic texts, constructs directed citation graphs,
 * and identifies bibliographic overlap anomalies and co-citation network clusters.
 */

export interface CitationItem {
  rawText: string;
  authors: string[];
  year: number | null;
  normalizedKey: string;
}

export interface CitationNode {
  id: string;
  label: string;
  type: 'document' | 'citation';
}

export interface CitationEdge {
  source: string;
  target: string;
  weight: number;
}

export interface CitationGraph {
  nodes: CitationNode[];
  edges: CitationEdge[];
}

export interface CitationAnomaly {
  citationKey: string;
  referencingDocIds: string[];
  coOccurrenceCount: number;
  suspicionScore: number;
}

/**
 * Extracts formatted citations (e.g. Smith et al. (2020), Johnson & Lee, 2021) from text.
 */
export function extractCitationsFromText(text: string): CitationItem[] {
  const citations: CitationItem[] = [];
  const citationRegex = /([A-Z][a-zA-Z]+(?:\s+et\s+al\.|(?:\s+(?:and|&)\s+[A-Z][a-zA-Z]+))?)\s*\((\d{4})\)/g;

  let match: RegExpExecArray | null;
  while ((match = citationRegex.exec(text)) !== null) {
    const rawText = match[0];
    const authorsRaw = match[1];
    const year = parseInt(match[2], 10);

    const authors = authorsRaw
      .replace(/\s+et\s+al\./g, '')
      .split(/\s+(?:and|&)\s+/)
      .map(a => a.trim());

    const mainAuthor = authors[0] || 'Unknown';
    const normalizedKey = `${mainAuthor.toLowerCase()}_${year}`;

    citations.push({
      rawText,
      authors,
      year,
      normalizedKey,
    });
  }

  return citations;
}

/**
 * Builds a bipartite directed graph mapping documents to their cited reference nodes.
 */
export function buildCitationGraph(
  documents: Array<{ id: string; title: string; content: string }>
): CitationGraph {
  const nodesMap = new Map<string, CitationNode>();
  const edges: CitationEdge[] = [];

  for (const doc of documents) {
    const docNodeId = `doc_${doc.id}`;
    if (!nodesMap.has(docNodeId)) {
      nodesMap.set(docNodeId, { id: docNodeId, label: doc.title, type: 'document' });
    }

    const citations = extractCitationsFromText(doc.content);
    for (const cite of citations) {
      const citeNodeId = `cite_${cite.normalizedKey}`;
      if (!nodesMap.has(citeNodeId)) {
        nodesMap.set(citeNodeId, { id: citeNodeId, label: cite.rawText, type: 'citation' });
      }

      edges.push({
        source: docNodeId,
        target: citeNodeId,
        weight: 1.0,
      });
    }
  }

  return {
    nodes: Array.from(nodesMap.values()),
    edges,
  };
}

/**
 * Detects co-citation anomalies (shared identical citation lists across independent student submissions).
 */
export function detectCitationAnomalies(
  graph: CitationGraph,
  minSharedCitations = 2
): CitationAnomaly[] {
  const citationToDocsMap = new Map<string, Set<string>>();

  for (const edge of graph.edges) {
    if (!citationToDocsMap.has(edge.target)) {
      citationToDocsMap.set(edge.target, new Set());
    }
    citationToDocsMap.get(edge.target)!.add(edge.source);
  }

  const anomalies: CitationAnomaly[] = [];

  for (const [citeNodeId, docSet] of citationToDocsMap.entries()) {
    if (docSet.size >= minSharedCitations) {
      const docIds = Array.from(docSet).map(id => id.replace(/^doc_/, ''));
      const coOccurrenceCount = docSet.size;
      const suspicionScore = Math.min(1.0, (coOccurrenceCount - 1) * 0.4);

      anomalies.push({
        citationKey: citeNodeId.replace(/^cite_/, ''),
        referencingDocIds: docIds,
        coOccurrenceCount,
        suspicionScore,
      });
    }
  }

  return anomalies.sort((a, b) => b.suspicionScore - a.suspicionScore);
}
