import { describe, it, expect } from 'vitest';
import { WinnowingEngine } from './WinnowingEngine';

describe('WinnowingEngine', () => {
  const engine = new WinnowingEngine({ kgramSize: 5, windowSize: 3 });

  it('should sanitize input text properly', () => {
    const text = "Hello, World! 123";
    expect(engine.sanitizeText(text)).toBe("helloworld123");
  });

  it('should winnow fingerprint hashes with sliding window', () => {
    const text = "the quick brown fox jumps over the lazy dog";
    const fingerprints = engine.winnow(text);
    expect(fingerprints.length).toBeGreaterThan(0);
    fingerprints.forEach(fp => {
      expect(typeof fp.hash).toBe('number');
      expect(typeof fp.position).toBe('number');
    });
  });

  it('should achieve high containment score for near-duplicate documents', () => {
    const textA = "Enterprise grade semantic plagiarism detection pipeline with winnowing.";
    const textB = "Enterprise grade semantic plagiarism detection pipeline with winnowing and extra words.";

    const fpA = engine.winnow(textA);
    const fpB = engine.winnow(textB);

    const score = engine.computeContainmentScore(fpA, fpB);
    expect(score).toBeGreaterThan(0.7);
  });
});
