import { describe, it, expect } from 'vitest';
import {
  winnowDocument,
  compareWinnowedFingerprints,
} from './WinnowingLocalSubstringFingerprintingEngine';

describe('WinnowingLocalSubstringFingerprintingEngine', () => {
  const textA = `The quick brown fox jumps over the lazy dog repeatedly in the afternoon sun.`;
  const textB = `The quick brown fox leaps over the lazy dog repeatedly during the afternoon sun.`;

  it('should generate winnowed fingerprints with positions', () => {
    const result = winnowDocument(textA, 5, 4);

    expect(result).toBeDefined();
    expect(result.fingerprints.length).toBeGreaterThan(0);
    expect(result.totalKGrams).toBeGreaterThan(0);
    expect(result.fingerprints[0]).toHaveProperty('hash');
    expect(result.fingerprints[0]).toHaveProperty('position');
  });

  it('should detect local substring overlap between close variations', () => {
    const fpA = winnowDocument(textA, 5, 4);
    const fpB = winnowDocument(textB, 5, 4);

    const comparison = compareWinnowedFingerprints(fpA, fpB);

    expect(comparison).toBeDefined();
    expect(comparison.matchingHashCount).toBeGreaterThan(0);
    expect(comparison.overlapSimilarity).toBeGreaterThan(0.3);
    expect(comparison.isPlagiarizedSubstring).toBe(true);
  });
});
