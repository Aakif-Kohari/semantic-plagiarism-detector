/**
 * Multi-Language Neural Code Clone & AST Semantic Hashing Pipeline.
 * Integrates AST normalization, SimHash LSH fingerprinting, and Levenshtein token edit distance.
 */

import { ASTCodeCloneNormalizer, NormalizedASTResult } from './ASTCodeCloneNormalizer';
import { SimHashCodeCloneEngine } from './SimHashCodeCloneEngine';
import { ASTEditDistanceDetector, CodeRefactoringMetrics } from './ASTEditDistanceDetector';

export enum CodeCloneCategory {
  TYPE_1_EXACT = 'TYPE_1_EXACT',
  TYPE_2_RENAMED = 'TYPE_2_RENAMED',
  TYPE_3_REFACTORED = 'TYPE_3_REFACTORED',
  TYPE_4_SEMANTIC = 'TYPE_4_SEMANTIC',
  DISTINCT = 'DISTINCT'
}

export interface CodeCloneAuditReport {
  codeSnippetA: NormalizedASTResult;
  codeSnippetB: NormalizedASTResult;
  simHashSimilarity: number;
  refactoringMetrics: CodeRefactoringMetrics;
  cloneCategory: CodeCloneCategory;
  timestamp: string;
}

export class NeuralASTCodeClonePipeline {
  private normalizer: ASTCodeCloneNormalizer;
  private simHashEngine: SimHashCodeCloneEngine;
  private editDetector: ASTEditDistanceDetector;

  constructor() {
    this.normalizer = new ASTCodeCloneNormalizer();
    this.simHashEngine = new SimHashCodeCloneEngine(64);
    this.editDetector = new ASTEditDistanceDetector();
  }

  public auditCodeSnippets(codeA: string, codeB: string): CodeCloneAuditReport {
    const astA = this.normalizer.normalizeCode(codeA);
    const astB = this.normalizer.normalizeCode(codeB);

    const hashA = this.simHashEngine.computeSimHash(astA.tokens);
    const hashB = this.simHashEngine.computeSimHash(astB.tokens);
    const simHashSim = this.simHashEngine.computeSimHashSimilarity(hashA, hashB);

    const refactoringMetrics = this.editDetector.analyzeRefactoring(astA.tokens, astB.tokens);

    let cloneCategory = CodeCloneCategory.DISTINCT;
    if (codeA.trim() === codeB.trim()) {
      cloneCategory = CodeCloneCategory.TYPE_1_EXACT;
    } else if (astA.normalizedCode === astB.normalizedCode) {
      cloneCategory = CodeCloneCategory.TYPE_2_RENAMED;
    } else if (refactoringMetrics.similarityRatio >= 0.7) {
      cloneCategory = CodeCloneCategory.TYPE_3_REFACTORED;
    } else if (simHashSim >= 0.65) {
      cloneCategory = CodeCloneCategory.TYPE_4_SEMANTIC;
    }

    return {
      codeSnippetA: astA,
      codeSnippetB: astB,
      simHashSimilarity: simHashSim,
      refactoringMetrics,
      cloneCategory,
      timestamp: new Date().toISOString()
    };
  }
}
