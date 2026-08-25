/**
 * OCR Noise Reduction & Image-Text Normalizer Engine.
 * Filters OCR artifacts, corrects spellings/character confusion (e.g. 0 -> O, 1 -> l),
 * and computes OCR confidence scores.
 */

export interface OCRNormalizationResult {
  rawText: string;
  cleanedText: string;
  confidenceScore: number;
  correctedArtifactsCount: number;
}

export class OCRNoiseReductionEngine {
  private characterCorrections: [RegExp, string][];

  constructor() {
    this.characterCorrections = [
      [/1(?=[a-z])/g, 'l'],
      [/0(?=[a-z])/g, 'o'],
      [/5(?=[a-z])/g, 's'],
      [/8(?=[a-z])/g, 'b']
    ];
  }

  public cleanOCRText(ocrText: string): OCRNormalizationResult {
    if (!ocrText) {
      return {
        rawText: '',
        cleanedText: '',
        confidenceScore: 0,
        correctedArtifactsCount: 0
      };
    }

    let correctedCount = 0;
    let cleanedText = ocrText;

    this.characterCorrections.forEach(([pattern, replacement]) => {
      const matches = cleanedText.match(pattern);
      if (matches) {
        correctedCount += matches.length;
        cleanedText = cleanedText.replace(pattern, replacement);
      }
    });

    cleanedText = cleanedText.replace(/[^\x20-\x7E\n]/g, '').trim();
    const tokens = ocrText.split(/\s+/);
    const confidenceScore = Math.max(0.5, Math.min(0.99, 1.0 - (correctedCount / Math.max(1, tokens.length))));

    return {
      rawText: ocrText,
      cleanedText,
      confidenceScore: Math.round(confidenceScore * 100) / 100,
      correctedArtifactsCount: correctedCount
    };
  }
}
