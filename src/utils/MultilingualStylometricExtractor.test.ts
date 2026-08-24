import { describe, it, expect } from 'vitest';
import { MultilingualStylometricExtractor } from './MultilingualStylometricExtractor';

describe('MultilingualStylometricExtractor', () => {
  const extractor = new MultilingualStylometricExtractor();

  it('should extract stylometric feature vector accurately', () => {
    const text = "Academic writing requires rigorous research. Stylometric analysis evaluates sentence length and lexical diversity metrics.";
    const vector = extractor.extractVector(text);

    expect(vector.totalWords).toBeGreaterThan(10);
    expect(vector.totalSentences).toBe(2);
    expect(vector.meanSentenceLength).toBeGreaterThan(5);
    expect(vector.typeTokenRatio).toBeGreaterThan(0.5);
    expect(vector.yulesKMetric).toBeGreaterThan(0);
  });
});
