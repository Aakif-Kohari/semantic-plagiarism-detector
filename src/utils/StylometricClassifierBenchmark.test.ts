import { describe, it, expect } from 'vitest';
import { StylometricClassifierBenchmark } from './StylometricClassifierBenchmark';

describe('StylometricClassifierBenchmark', () => {
  it('should compute precision, recall, and F1-score', () => {
    const metrics = StylometricClassifierBenchmark.calculateF1(80, 10, 10);
    expect(metrics.precision).toBe(0.889);
    expect(metrics.recall).toBe(0.889);
    expect(metrics.f1Score).toBe(0.889);
  });
});
