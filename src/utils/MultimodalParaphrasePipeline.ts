/**
 * Unified Multimodal PDF OCR & Neural Paraphrase Audit Pipeline.
 * Synthesizes PDF layout extraction, OCR noise reduction, and sentence-level paraphrase alignment.
 */

import { PDFLayoutStructureExtractor, PDFNormalizedDocument } from './PDFLayoutStructureExtractor';
import { OCRNoiseReductionEngine, OCRNormalizationResult } from './OCRNoiseReductionEngine';
import { NeuralParaphraseMatcher, SentenceAlignmentPair } from './NeuralParaphraseMatcher';

export interface MultimodalAuditReport {
  pdfStructure: PDFNormalizedDocument;
  ocrMetrics: OCRNormalizationResult;
  paraphraseAlignments: SentenceAlignmentPair[];
  overallParaphrasePercentage: number;
  isPlagiarismFlagged: boolean;
  timestamp: string;
}

export class MultimodalParaphrasePipeline {
  private pdfExtractor: PDFLayoutStructureExtractor;
  private ocrEngine: OCRNoiseReductionEngine;
  private paraphraseMatcher: NeuralParaphraseMatcher;

  constructor() {
    this.pdfExtractor = new PDFLayoutStructureExtractor();
    this.ocrEngine = new OCRNoiseReductionEngine();
    this.paraphraseMatcher = new NeuralParaphraseMatcher();
  }

  public auditMultimodalDocument(rawPdfText: string, comparisonCorpusText: string): MultimodalAuditReport {
    const pdfStructure = this.pdfExtractor.extractPageBlocks(rawPdfText);
    const ocrMetrics = this.ocrEngine.cleanOCRText(pdfStructure.fullNormalizedText);
    const paraphraseAlignments = this.paraphraseMatcher.alignParaphrasedSentences(
      ocrMetrics.cleanedText,
      comparisonCorpusText
    );

    const totalSentences = this.paraphraseMatcher.splitSentences(ocrMetrics.cleanedText).length || 1;
    const paraphrasePercentage = Math.round((paraphraseAlignments.length / totalSentences) * 100);

    return {
      pdfStructure,
      ocrMetrics,
      paraphraseAlignments,
      overallParaphrasePercentage: paraphrasePercentage,
      isPlagiarismFlagged: paraphrasePercentage >= 30,
      timestamp: new Date().toISOString()
    };
  }
}
