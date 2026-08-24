import { describe, it, expect } from 'vitest';
import { OCRNoiseReductionEngine } from './OCRNoiseReductionEngine';

describe('OCRNoiseReductionEngine', () => {
  const engine = new OCRNoiseReductionEngine();

  it('should clean OCR artifacts and estimate confidence score', () => {
    const rawOcr = "Th1s 1s a sample OCR txt text doc";
    const result = engine.cleanOCRText(rawOcr);

    expect(result.cleanedText).toContain('Thls');
    expect(result.correctedArtifactsCount).toBeGreaterThan(0);
    expect(result.confidenceScore).toBeGreaterThan(0.5);
  });
});
