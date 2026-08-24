/**
 * OCR Quality Telemetry & Noise Analytics Utility.
 * Evaluates document OCR quality score metrics to trigger manual review workflows.
 */

export class OCRQualityTelemetryEngine {
  public static evaluateOCRHealth(confidenceScore: number, correctedCount: number): { health: 'EXCELLENT' | 'FAIR' | 'POOR'; requiresHumanReview: boolean } {
    if (confidenceScore >= 0.9 && correctedCount < 5) {
      return { health: 'EXCELLENT', requiresHumanReview: false };
    } else if (confidenceScore >= 0.7) {
      return { health: 'FAIR', requiresHumanReview: false };
    } else {
      return { health: 'POOR', requiresHumanReview: true };
    }
  }
}
