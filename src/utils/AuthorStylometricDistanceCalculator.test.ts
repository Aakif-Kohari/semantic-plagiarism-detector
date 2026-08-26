import { describe, it, expect } from 'vitest';
import { AuthorStylometricDistanceCalculator } from './AuthorStylometricDistanceCalculator';
import { MultilingualStylometricExtractor } from './MultilingualStylometricExtractor';

describe('AuthorStylometricDistanceCalculator', () => {
  const extractor = new MultilingualStylometricExtractor();
  const calculator = new AuthorStylometricDistanceCalculator();

  it('should compute high cosine similarity for similar stylistic vectors', () => {
    const textA = "The system performs continuous telemetry monitoring and alerting.";
    const textB = "The platform executes ongoing metric surveillance and notification triggers.";

    const vecA = extractor.extractVector(textA);
    const vecB = extractor.extractVector(textB);

    const sim = calculator.computeCosineSimilarity(vecA, vecB);
    expect(sim).toBeGreaterThan(0.8);
  });
});
