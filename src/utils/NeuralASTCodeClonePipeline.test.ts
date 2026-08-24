import { describe, it, expect } from 'vitest';
import { NeuralASTCodeClonePipeline, CodeCloneCategory } from './NeuralASTCodeClonePipeline';

describe('NeuralASTCodeClonePipeline', () => {
  const pipeline = new NeuralASTCodeClonePipeline();

  it('should categorize exact code clones as TYPE_1_EXACT', () => {
    const code = "function compute() { return 42; }";
    const report = pipeline.auditCodeSnippets(code, code);
    expect(report.cloneCategory).toBe(CodeCloneCategory.TYPE_1_EXACT);
  });

  it('should categorize renamed variables as TYPE_2_RENAMED', () => {
    const codeA = "function add(x, y) { return x + y; }";
    const codeB = "function add(val1, val2) { return val1 + val2; }";
    const report = pipeline.auditCodeSnippets(codeA, codeB);
    expect(report.cloneCategory).toBe(CodeCloneCategory.TYPE_2_RENAMED);
  });

  it('should categorize refactored logic as TYPE_3_REFACTORED', () => {
    const codeA = "function sum(arr) { let total = 0; for(let i=0; i<arr.length; i++) total += arr[i]; return total; }";
    const codeB = "function sum(arr) { let total = 0; arr.forEach(val => total += val); return total; }";
    const report = pipeline.auditCodeSnippets(codeA, codeB);
    expect([CodeCloneCategory.TYPE_3_REFACTORED, CodeCloneCategory.TYPE_4_SEMANTIC]).toContain(report.cloneCategory);
  });
});
