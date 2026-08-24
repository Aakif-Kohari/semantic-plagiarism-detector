import { describe, it, expect } from 'vitest';
import { ASTCodeCloneNormalizer } from './ASTCodeCloneNormalizer';

describe('ASTCodeCloneNormalizer', () => {
  const normalizer = new ASTCodeCloneNormalizer();

  it('should tokenize JavaScript/TypeScript code snippet', () => {
    const code = "function add(a, b) { return a + b; }";
    const tokens = normalizer.tokenize(code);
    expect(tokens.length).toBeGreaterThan(0);
    expect(tokens).toContain('function');
  });

  it('should normalize identifiers and literals to canonical form', () => {
    const code = "function computeSum(x, y) { let total = x + y + 10; return total; }";
    const result = normalizer.normalizeCode(code);

    expect(result.normalizedCode).toContain('VAR_0');
    expect(result.normalizedCode).toContain('LIT_NUM');
    expect(result.nodeCount).toBeGreaterThan(5);
    expect(result.depth).toBeGreaterThan(1);
  });
});
