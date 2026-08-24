/**
 * Levenshtein AST Edit Distance Code Refactoring Detector.
 * Computes exact tree/token edit distances to detect Type-3 refactored code clones.
 */

export interface CodeRefactoringMetrics {
  editDistance: number;
  similarityRatio: number;
  addedTokens: number;
  deletedTokens: number;
}

export class ASTEditDistanceDetector {

  public computeTokenEditDistance(tokensA: string[], tokensB: string[]): number {
    const m = tokensA.length;
    const n = tokensB.length;
    const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

    for (let i = 0; i <= m; i++) dp[i][0] = i;
    for (let j = 0; j <= n; j++) dp[0][j] = j;

    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        if (tokensA[i - 1] === tokensB[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1];
        } else {
          dp[i][j] = 1 + Math.min(
            dp[i - 1][j],
            dp[i][j - 1],
            dp[i - 1][j - 1]
          );
        }
      }
    }

    return dp[m][n];
  }

  public analyzeRefactoring(tokensA: string[], tokensB: string[]): CodeRefactoringMetrics {
    const editDistance = this.computeTokenEditDistance(tokensA, tokensB);
    const maxLen = Math.max(tokensA.length, tokensB.length);
    const similarityRatio = maxLen > 0 ? (maxLen - editDistance) / maxLen : 1.0;

    const setA = new Set(tokensA);
    const setB = new Set(tokensB);

    let addedTokens = 0;
    tokensB.forEach(t => {
      if (!setA.has(t)) addedTokens++;
    });

    let deletedTokens = 0;
    tokensA.forEach(t => {
      if (!setB.has(t)) deletedTokens++;
    });

    return {
      editDistance,
      similarityRatio: Math.round(similarityRatio * 1000) / 1000,
      addedTokens,
      deletedTokens
    };
  }
}
