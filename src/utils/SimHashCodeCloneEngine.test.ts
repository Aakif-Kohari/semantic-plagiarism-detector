import { describe, it, expect } from 'vitest';
import { SimHashCodeCloneEngine } from './SimHashCodeCloneEngine';

describe('SimHashCodeCloneEngine', () => {
  const simHashEngine = new SimHashCodeCloneEngine(64);

  it('should compute 64-bit binary SimHash fingerprint', () => {
    const tokens = ['function', 'VAR_0', '(', ')', '{', 'return', 'LIT_NUM', '}'];
    const hash = simHashEngine.computeSimHash(tokens);
    expect(hash.length).toBe(64);
    expect(hash).toMatch(/^[01]{64}$/);
  });

  it('should evaluate Hamming distance between code fingerprints', () => {
    const tokensA = ['function', 'VAR_0', '(', ')', '{', 'return', 'LIT_NUM', '}'];
    const tokensB = ['function', 'VAR_0', '(', ')', '{', 'return', 'LIT_NUM', ';', '}'];

    const hashA = simHashEngine.computeSimHash(tokensA);
    const hashB = simHashEngine.computeSimHash(tokensB);

    const similarity = simHashEngine.computeSimHashSimilarity(hashA, hashB);
    expect(similarity).toBeGreaterThan(0.7);
  });
});
