import { describe, it, expect } from 'vitest';
import { MultimodalUIOverlayTransformer } from './MultimodalUIOverlayTransformer';
import { PDFTextBlock } from './PDFLayoutStructureExtractor';
import { SentenceAlignmentPair } from './NeuralParaphraseMatcher';

describe('MultimodalUIOverlayTransformer', () => {
  it('should transform PDF blocks and alignments into bounding box UI highlights', () => {
    const blocks: PDFTextBlock[] = [
      {
        blockId: 'blk_1',
        pageNumber: 1,
        text: 'Deep neural networks enable automated pattern recognition.',
        bbox: { x: 50, y: 100, width: 200, height: 20 },
        isHeaderOrFooter: false
      }
    ];

    const alignments: SentenceAlignmentPair[] = [
      {
        sentenceA: 'Deep neural networks enable automated pattern recognition.',
        sentenceB: 'Deep learning neural nets allow automated pattern detection.',
        similarityScore: 0.85,
        isParaphrase: true
      }
    ];

    const highlights = MultimodalUIOverlayTransformer.transformToUIHighlights(blocks, alignments);
    expect(highlights.length).toBe(1);
    expect(highlights[0].color).toBe('#ef4444');
  });
});
