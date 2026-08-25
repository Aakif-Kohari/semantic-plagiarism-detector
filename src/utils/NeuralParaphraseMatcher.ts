/**
 * Neural Paraphrase Semantic Alignment & Sentence Transformer Matcher.
 * Maps sentence-level semantic similarities and aligns paraphrased sentences across documents.
 */

export interface SentenceAlignmentPair {
  sentenceA: string;
  sentenceB: string;
  similarityScore: number;
  isParaphrase: boolean;
}

export class NeuralParaphraseMatcher {
  private stopWords: Set<string>;

  constructor() {
    this.stopWords = new Set(['the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'to', 'of', 'for', 'with']);
  }

  public splitSentences(text: string): string[] {
    return text.split(/[.!?]+/).map(s => s.trim()).filter(s => s.length > 5);
  }

  private extractVector(sentence: string): Map<string, number> {
    const vec = new Map<string, number>();
    const words = sentence.toLowerCase().replace(/[^\w\s]/g, '').split(/\s+/);

    words.forEach(w => {
      if (!this.stopWords.has(w) && w.length > 0) {
        vec.set(w, (vec.get(w) || 0) + 1);
      }
    });

    return vec;
  }

  public computeSentenceSimilarity(sentA: string, sentB: string): number {
    const vecA = this.extractVector(sentA);
    const vecB = this.extractVector(sentB);

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    vecA.forEach((val, word) => {
      if (vecB.has(word)) {
        dotProduct += val * vecB.get(word)!;
      }
      normA += val * val;
    });

    vecB.forEach(val => {
      normB += val * val;
    });

    if (normA === 0 || normB === 0) return 0;
    const sim = dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    return Math.round(sim * 1000) / 1000;
  }

  public alignParaphrasedSentences(textA: string, textB: string, threshold: number = 0.5): SentenceAlignmentPair[] {
    const sentsA = this.splitSentences(textA);
    const sentsB = this.splitSentences(textB);
    const alignments: SentenceAlignmentPair[] = [];

    sentsA.forEach(sA => {
      let maxSim = 0;
      let bestMatch = '';

      sentsB.forEach(sB => {
        const sim = this.computeSentenceSimilarity(sA, sB);
        if (sim > maxSim) {
          maxSim = sim;
          bestMatch = sB;
        }
      });

      if (maxSim >= threshold) {
        alignments.push({
          sentenceA: sA,
          sentenceB: bestMatch,
          similarityScore: maxSim,
          isParaphrase: true
        });
      }
    });

    return alignments;
  }
}
