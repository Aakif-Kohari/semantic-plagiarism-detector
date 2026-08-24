import { describe, it, expect } from 'vitest';
import { PDFLayoutStructureExtractor } from './PDFLayoutStructureExtractor';

describe('PDFLayoutStructureExtractor', () => {
  const extractor = new PDFLayoutStructureExtractor();

  it('should extract PDF page blocks and filter header/footer content', () => {
    const pdfText = `--- Page 1 ---
Header Document Title
Introduction to deep neural network plagiarism detection.
--- Page 2 ---
Methodology and vector embeddings evaluation.
Page 2 of 2`;

    const doc = extractor.extractPageBlocks(pdfText, 'test_pdf');
    expect(doc.totalPages).toBe(2);
    expect(doc.blocks.length).toBe(4);
    expect(doc.fullNormalizedText).toContain('Introduction to deep neural network');
  });
});
