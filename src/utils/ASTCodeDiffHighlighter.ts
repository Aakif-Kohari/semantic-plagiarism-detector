/**
 * Code Diff Highlighting Utility.
 * Highlights token diffs between two AST normalized token streams.
 */

export interface TokenDiffResult {
  token: string;
  type: 'ADDED' | 'REMOVED' | 'UNCHANGED';
}

export class ASTCodeDiffHighlighter {
  public static computeTokenDiff(tokensA: string[], tokensB: string[]): TokenDiffResult[] {
    const diffs: TokenDiffResult[] = [];
    const setB = new Set(tokensB);
    const setA = new Set(tokensA);

    tokensA.forEach(t => {
      if (setB.has(t)) {
        diffs.push({ token: t, type: 'UNCHANGED' });
      } else {
        diffs.push({ token: t, type: 'REMOVED' });
      }
    });

    tokensB.forEach(t => {
      if (!setA.has(t)) {
        diffs.push({ token: t, type: 'ADDED' });
      }
    });

    return diffs;
  }
}
