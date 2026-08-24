import { describe, it, expect } from 'vitest';
import { IntraDocumentStyleAnomalyDetector } from './IntraDocumentStyleAnomalyDetector';

describe('IntraDocumentStyleAnomalyDetector', () => {
  const detector = new IntraDocumentStyleAnomalyDetector();

  it('should detect stylistic shifts across paragraph segments', () => {
    const doc = `First paragraph is short and simple. It has brief sentences.

    Second paragraph contains extremely complex, multifaceted, and convoluted academic phrasing engineered specifically to increase sentence length drastically beyond normal limits.

    Third paragraph returns to normal structure.`;

    const segments = detector.detectStyleShift(doc, 1.0);
    expect(segments.length).toBe(3);
    expect(segments.some(s => s.anomalyScore > 0)).toBe(true);
  });
});
