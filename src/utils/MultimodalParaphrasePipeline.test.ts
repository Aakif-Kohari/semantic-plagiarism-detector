import { describe, it, expect } from 'vitest';
import { MultimodalParaphrasePipeline } from './MultimodalParaphrasePipeline';

describe('MultimodalParaphrasePipeline', () => {
  const pipeline = new MultimodalParaphrasePipeline();

  it('should audit raw PDF OCR text against reference document', () => {
    const rawPdf = `--- Page 1 ---
Deep 1earning node models compute gradient vector updates during backpropagation.`;
    const corpusText = "Deep learning neural network models calculate gradient updates in backpropagation.";

    const report = pipeline.auditMultimodalDocument(rawPdf, corpusText);
    expect(report.pdfStructure.totalPages).toBe(1);
    expect(report.ocrMetrics.cleanedText).toContain('learning');
    expect(report.paraphraseAlignments.length).toBeGreaterThan(0);
  });
});
