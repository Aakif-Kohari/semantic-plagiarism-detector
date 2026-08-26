/**
 * Fuzzy Token Edit Distance Engine
 * Computes exact Levenshtein distance at the word/token level to identify near-duplicate passages,
 * word substitutions, insertions, and deletions across student submissions.
 */

export interface TokenEditDistanceResult {
  similarityScore: number;
  tokenEditDistance: number;
  tokensDocA: number;
  tokensDocB: number;
  isFuzzyMatch: boolean;
  alignmentSummary: {
    exactMatches: number;
    substitutions: number;
    insertions: number;
    deletions: number;
  };
}

/**
 * Tokenizes text into normalized word tokens.
 */
export function tokenizeText(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, '')
    .split(/\s+/)
    .filter(t => t.length > 0);
}

/**
 * Computes Levenshtein edit distance between two token arrays using DP table.
 */
export function tokenLevenshteinDistance(tokensA: string[], tokensB: string[]): number {
  const m = tokensA.length;
  const n = tokensB.length;

  if (m === 0) return n;
  if (n === 0) return m;

  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const cost = tokensA[i - 1] === tokensB[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,      // Deletion
        dp[i][j - 1] + 1,      // Insertion
        dp[i - 1][j - 1] + cost // Substitution
      );
    }
  }

  return dp[m][n];
}

/**
 * Calculates normalized similarity score [0.0, 1.0] derived from token Levenshtein distance.
 */
export function calculateTokenSimilarity(textA: string, textB: string): number {
  const tokensA = tokenizeText(textA);
  const tokensB = tokenizeText(textB);

  const maxLen = Math.max(tokensA.length, tokensB.length);
  if (maxLen === 0) return 1.0;

  const dist = tokenLevenshteinDistance(tokensA, tokensB);
  return Math.max(0.0, 1.0 - dist / maxLen);
}

/**
 * Performs full fuzzy token match comparison between two passages.
 */
export function compareFuzzyTokenMatch(
  textA: string,
  textB: string,
  similarityThreshold = 0.70
): TokenEditDistanceResult {
  const tokensA = tokenizeText(textA);
  const tokensB = tokenizeText(textB);

  const maxLen = Math.max(tokensA.length, tokensB.length);
  const dist = tokenLevenshteinDistance(tokensA, tokensB);
  const similarityScore = maxLen > 0 ? Math.max(0.0, 1.0 - dist / maxLen) : 1.0;

  // Simple alignment stats estimation
  let exactMatches = 0;
  const setB = new Set(tokensB);
  for (const t of tokensA) {
    if (setB.has(t)) exactMatches++;
  }

  const substitutions = Math.min(dist, Math.min(tokensA.length, tokensB.length));
  const insertions = Math.max(0, tokensB.length - tokensA.length);
  const deletions = Math.max(0, tokensA.length - tokensB.length);

  return {
    similarityScore,
    tokenEditDistance: dist,
    tokensDocA: tokensA.length,
    tokensDocB: tokensB.length,
    isFuzzyMatch: similarityScore >= similarityThreshold,
    alignmentSummary: {
      exactMatches,
      substitutions,
      insertions,
      deletions,
    },
  };
}
