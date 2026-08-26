import { describe, it, expect } from 'vitest';
import { NeuralParaphraseMatcher } from './NeuralParaphraseMatcher';

describe('NeuralParaphraseMatcher', () => {
  const matcher = new NeuralParaphraseMatcher();

  it('should align semantically similar paraphrased sentences across documents', () => {
    const docA = "Machine learning models require clean training datasets for optimal accuracy.";
    const docB = "Machine learning algorithms need clean training data for higher accuracy metrics.";

    const alignments = matcher.alignParaphrasedSentences(docA, docB, 0.4);
    expect(alignments.length).toBe(1);
    expect(alignments[0].isParaphrase).toBe(true);
  });
});
