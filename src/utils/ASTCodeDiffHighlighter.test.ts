import { describe, it, expect } from 'vitest';
import { ASTCodeDiffHighlighter } from './ASTCodeDiffHighlighter';

describe('ASTCodeDiffHighlighter', () => {
  it('should compute token diffs between two token sets', () => {
    const tokensA = ['function', 'add', 'a'];
    const tokensB = ['function', 'add', 'b'];

    const diffs = ASTCodeDiffHighlighter.computeTokenDiff(tokensA, tokensB);
    expect(diffs.length).toBe(4);
    expect(diffs.some(d => d.type === 'ADDED')).toBe(true);
    expect(diffs.some(d => d.type === 'REMOVED')).toBe(true);
  });
});
