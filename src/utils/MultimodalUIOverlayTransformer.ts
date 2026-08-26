/**
 * Document Bounding Box Side-by-Side Visual Highlighter Data Transformer.
 * Generates coordinate bounding box overlays for displaying matched PDF blocks side-by-side in React UI.
 */

import { PDFTextBlock } from './PDFLayoutStructureExtractor';
import { SentenceAlignmentPair } from './NeuralParaphraseMatcher';

export interface BoundingBoxHighlight {
  blockId: string;
  pageNumber: number;
  x: number;
  y: number;
  width: number;
  height: number;
  matchedText: string;
  similarityScore: number;
  color: string;
}

export class MultimodalUIOverlayTransformer {
  public static transformToUIHighlights(
    blocks: PDFTextBlock[],
    alignments: SentenceAlignmentPair[]
  ): BoundingBoxHighlight[] {
    const highlights: BoundingBoxHighlight[] = [];

    alignments.forEach(align => {
      const matchingBlock = blocks.find(b => b.text.includes(align.sentenceA) || align.sentenceA.includes(b.text));
      if (matchingBlock) {
        highlights.push({
          blockId: matchingBlock.blockId,
          pageNumber: matchingBlock.pageNumber,
          x: matchingBlock.bbox.x,
          y: matchingBlock.bbox.y,
          width: matchingBlock.bbox.width,
          height: matchingBlock.bbox.height,
          matchedText: align.sentenceA,
          similarityScore: align.similarityScore,
          color: align.similarityScore > 0.8 ? '#ef4444' : '#f59e0b'
        });
      }
    });

    return highlights;
  }
}
