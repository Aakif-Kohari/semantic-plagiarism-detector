/**
 * Winnowing Local Substring Fingerprinting Engine
 * Implements the robust Winnowing algorithm (Schleimer et al.) to extract guaranteed local substring matches
 * using k-gram hashing and sliding window min-hash selection.
 */

export interface FingerprintPoint {
  hash: number;
  position: number;
}

export interface WinnowingResult {
  fingerprints: FingerprintPoint[];
  totalKGrams: number;
  kGramSize: number;
  windowSize: number;
}

export interface WinnowingComparisonResult {
  overlapSimilarity: number;
  matchingHashCount: number;
  totalUniqueFingerprintsA: number;
  totalUniqueFingerprintsB: number;
  isPlagiarizedSubstring: boolean;
}

/**
 * Normalizes string by stripping non-alphanumeric chars and converting to lowercase.
 */
function normalizeString(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]/g, '');
}

/**
 * Simple polynomial hash for k-gram strings.
 */
function hashKGram(kgram: string): number {
  let hash = 0;
  for (let i = 0; i < kgram.length; i++) {
    hash = (hash * 31 + kgram.charCodeAt(i)) % 2147483647;
  }
  return Math.abs(hash);
}

/**
 * Computes winnowed fingerprint set from document string.
 * Guarantee: Any substring match of length >= (w + k - 1) will be detected.
 */
export function winnowDocument(text: string, k = 5, w = 4): WinnowingResult {
  const clean = normalizeString(text);
  if (clean.length < k) {
    return { fingerprints: [], totalKGrams: 0, kGramSize: k, windowSize: w };
  }

  // 1. Generate k-gram hashes
  const hashes: number[] = [];
  for (let i = 0; i <= clean.length - k; i++) {
    hashes.push(hashKGram(clean.substring(i, i + k)));
  }

  // 2. Apply sliding window of size w
  const fingerprints: FingerprintPoint[] = [];
  let lastMinPos = -1;

  for (let i = 0; i <= hashes.length - w; i++) {
    let minHash = Infinity;
    let minPos = -1;

    // Select rightmost minimum in window
    for (let j = 0; j < w; j++) {
      const idx = i + j;
      if (hashes[idx] <= minHash) {
        minHash = hashes[idx];
        minPos = idx;
      }
    }

    if (minPos !== lastMinPos) {
      fingerprints.push({ hash: minHash, position: minPos });
      lastMinPos = minPos;
    }
  }

  return {
    fingerprints,
    totalKGrams: hashes.length,
    kGramSize: k,
    windowSize: w,
  };
}

/**
 * Compares two winnowed fingerprint sets to detect local plagiarized substring overlap.
 */
export function compareWinnowedFingerprints(
  resA: WinnowingResult,
  resB: WinnowingResult,
  similarityThreshold = 0.25
): WinnowingComparisonResult {
  const setA = new Set(resA.fingerprints.map(f => f.hash));
  const setB = new Set(resB.fingerprints.map(f => f.hash));

  if (setA.size === 0 || setB.size === 0) {
    return {
      overlapSimilarity: 0,
      matchingHashCount: 0,
      totalUniqueFingerprintsA: setA.size,
      totalUniqueFingerprintsB: setB.size,
      isPlagiarizedSubstring: false,
    };
  }

  let matchingHashCount = 0;
  for (const h of setA) {
    if (setB.has(h)) {
      matchingHashCount++;
    }
  }

  const unionSize = setA.size + setB.size - matchingHashCount;
  const overlapSimilarity = unionSize > 0 ? matchingHashCount / unionSize : 0;
  const isPlagiarizedSubstring = overlapSimilarity >= similarityThreshold;

  return {
    overlapSimilarity,
    matchingHashCount,
    totalUniqueFingerprintsA: setA.size,
    totalUniqueFingerprintsB: setB.size,
    isPlagiarizedSubstring,
  };
}
