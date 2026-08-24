import { describe, it, expect } from 'vitest';
import { ASTEditDistanceDetector } from './ASTEditDistanceDetector';

describe('ASTEditDistanceDetector', () => {
  const detector = new ASTEditDistanceDetector();

  it('should compute token edit distance between AST representations', () => {
    const tokensA = ['function', 'VAR_0', '(', ')', '{', 'return', 'LIT_NUM', '}'];
    const tokensB = ['function', 'VAR_0', '(', ')', '{', 'let', 'VAR_1', '=', 'LIT_NUM', ';', 'return', 'VAR_1', '}'];

    const dist = detector.computeTokenEditDistance(tokensA, tokensB);
    expect(dist).toBeGreaterThan(0);
  });

  it('should generate detailed code refactoring metrics', () => {
    const tokensA = ['const', 'VAR_0', '=', 'LIT_NUM'];
    const tokensB = ['let', 'VAR_0', '=', 'LIT_NUM'];

    const metrics = detector.analyzeRefactoring(tokensA, tokensB);
    expect(metrics.similarityRatio).toBeGreaterThan(0.5);
    expect(metrics.addedTokens).toBe(1);
    expect(metrics.deletedTokens).toBe(1);
  });
});
