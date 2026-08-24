/**
 * Intra-Document Stylometric Anomaly Visualizer Data Transformer.
 * Segments documents into paragraphs/sliding blocks to detect sudden stylistic shifts,
 * ghostwriting insertion, and multi-author plagiarism.
 */

import { MultilingualStylometricExtractor, StylometricVector } from './MultilingualStylometricExtractor';

export interface ParagraphStyleSegment {
  segmentIndex: number;
  textSnippet: string;
  vector: StylometricVector;
  anomalyScore: number;
  isOutlier: boolean;
}

export class IntraDocumentStyleAnomalyDetector {
  private extractor: MultilingualStylometricExtractor;

  constructor() {
    this.extractor = new MultilingualStylometricExtractor();
  }

  public detectStyleShift(documentText: string, thresholdZScore: number = 2.0): ParagraphStyleSegment[] {
    const paragraphs = documentText.split(/\n\s*\n/).filter(p => p.trim().length > 0);
    if (paragraphs.length === 0) return [];

    const segments: ParagraphStyleSegment[] = paragraphs.map((text, idx) => ({
      segmentIndex: idx,
      textSnippet: text.substring(0, 50) + (text.length > 50 ? '...' : ''),
      vector: this.extractor.extractVector(text),
      anomalyScore: 0,
      isOutlier: false
    }));

    const meanLengths = segments.map(s => s.vector.meanSentenceLength);
    const avgLen = meanLengths.reduce((a, b) => a + b, 0) / meanLengths.length;

    const stdDev = Math.sqrt(
      meanLengths.reduce((sq, n) => sq + Math.pow(n - avgLen, 2), 0) / meanLengths.length
    ) || 1;

    segments.forEach(seg => {
      const zScore = Math.abs(seg.vector.meanSentenceLength - avgLen) / stdDev;
      seg.anomalyScore = Math.round(zScore * 100) / 100;
      seg.isOutlier = zScore >= thresholdZScore;
    });

    return segments;
  }
}
