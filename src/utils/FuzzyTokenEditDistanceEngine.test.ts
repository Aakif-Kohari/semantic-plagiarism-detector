import { describe, it, expect } from 'vitest';
import {
  tokenLevenshteinDistance,
  calculateTokenSimilarity,
  compareFuzzyTokenMatch,
} from './FuzzyTokenEditDistanceEngine';

describe('FuzzyTokenEditDistanceEngine', () => {
  const textA = `The neural network model classifies complex images with high accuracy.`;
  const textB = `The deep neural network model classifies complicated images with high accuracy.`;

  it('should compute exact Levenshtein edit distance between token arrays', () => {
    const tokens1 = ['the', 'quick', 'brown', 'fox'];
    const tokens2 = ['the', 'fast', 'brown', 'fox'];

    const distance = tokenLevenshteinDistance(tokens1, tokens2);
    expect(distance).toBe(1);
  });

  it('should calculate normalized token similarity score', () => {
    const similarity = calculateTokenSimilarity(textA, textB);
    expect(similarity).toBeGreaterThan(0.7);
    expect(similarity).toBeLessThanOrEqual(1.0);
  });

  it('should identify near-duplicate fuzzy matches', () => {
    const match = compareFuzzyTokenMatch(textA, textB, 0.65);

    expect(match).toBeDefined();
    expect(match.isFuzzyMatch).toBe(true);
    expect(match.tokenEditDistance).toBeGreaterThan(0);
    expect(match.similarityScore).toBeGreaterThan(0.7);
  });
});
