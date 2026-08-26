import { describe, it, expect } from 'vitest';
import { OCRQualityTelemetryEngine } from './OCRQualityTelemetryEngine';

describe('OCRQualityTelemetryEngine', () => {
  it('should evaluate OCR health metrics', () => {
    const health = OCRQualityTelemetryEngine.evaluateOCRHealth(0.65, 12);
    expect(health.health).toBe('POOR');
    expect(health.requiresHumanReview).toBe(true);
  });
});
