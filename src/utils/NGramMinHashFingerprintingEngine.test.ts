import { describe, it, expect } from 'vitest';
import {
  generateNGramTokens,
  computeMinHashSignature,
  estimateJaccardSimilarityFromMinHash,
  compareDocumentsMinHash,
} from './NGramMinHashFingerprintingEngine';

describe('NGramMinHashFingerprintingEngine', () => {
  const docA = `The artificial intelligence models demonstrate unprecedented performance in processing natural language text and identifying complex patterns.`;
  const docB = `Artificial intelligence models show great performance in natural language text processing and pattern recognition.`;
  const docC = `Quantum computing leverages superposition and entanglement to execute complex calculations faster than classical supercomputers.`;

  it('should generate word n-grams correctly', () => {
    const nGrams = generateNGramTokens('The quick brown fox jumps', 3);
    expect(nGrams).toBeDefined();
    expect(nGrams.length).toBe(3);
    expect(nGrams[0]).toBe('the quick brown');
    expect(nGrams[1]).toBe('quick brown fox');
  });

  it('should compute fixed-size MinHash signature vector', () => {
    const signature = computeMinHashSignature(docA, 3, 64);
    expect(signature).toBeDefined();
    expect(signature.length).toBe(64);
  });

  it('should estimate high similarity for overlapping documents and low for unrelated', () => {
    const sigA = computeMinHashSignature(docA, 3, 64);
    expect(sigA.length).toBe(64);

    const matchAB = compareDocumentsMinHash(docA, docB, 3, 64);
    const matchAC = compareDocumentsMinHash(docA, docC, 3, 64);

    expect(matchAB.estimatedJaccardSimilarity).toBeGreaterThan(matchAC.estimatedJaccardSimilarity);
  });
});
