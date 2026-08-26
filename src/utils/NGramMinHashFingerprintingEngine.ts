/**
 * N-Gram MinHash Fingerprinting Engine
 * Generates character/word n-gram shingles and computes MinHash signatures with linear hash functions
 * to estimate Jaccard set similarity across large document corpora in O(K) time.
 */

export interface MinHashComparisonResult {
  estimatedJaccardSimilarity: number;
  exactNGramOverlapCount: number;
  signatureLength: number;
  nGramSize: number;
  isPlagiarismCandidate: boolean;
}

/**
 * Generates sliding window word n-gram tokens from raw text.
 */
export function generateNGramTokens(text: string, n = 3): string[] {
  const words = text
    .toLowerCase()
    .replace(/[^\w\s]/g, '')
    .split(/\s+/)
    .filter(w => w.length > 0);

  if (words.length < n) {
    return [words.join(' ')];
  }

  const nGrams: string[] = [];
  for (let i = 0; i <= words.length - n; i++) {
    nGrams.push(words.slice(i, i + n).join(' '));
  }
  return nGrams;
}

/**
 * Simple polynomial rolling hash function for string tokens.
 */
function hashString(str: string, seed: number): number {
  let hash = seed;
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 31 + str.charCodeAt(i)) % 2147483647;
  }
  return Math.abs(hash);
}

/**
 * Generates K pseudo-random linear hash coefficients (a_i, b_i).
 */
function generateHashCoefficients(k: number): Array<{ a: number; b: number }> {
  const coeffs: Array<{ a: number; b: number }> = [];
  const prime = 2147483647;
  for (let i = 0; i < k; i++) {
    const a = (i * 10007 + 12345) % (prime - 1) + 1;
    const b = (i * 20011 + 54321) % prime;
    coeffs.push({ a, b });
  }
  return coeffs;
}

/**
 * Computes a MinHash signature vector of fixed size numPermutations.
 */
export function computeMinHashSignature(
  text: string,
  nGramSize = 3,
  numPermutations = 64
): number[] {
  const nGrams = generateNGramTokens(text, nGramSize);
  const coeffs = generateHashCoefficients(numPermutations);
  const prime = 2147483647;

  const signature: number[] = new Array(numPermutations).fill(Infinity);

  for (const nGram of nGrams) {
    const baseHash = hashString(nGram, 17);
    for (let i = 0; i < numPermutations; i++) {
      const h = (coeffs[i].a * baseHash + coeffs[i].b) % prime;
      if (h < signature[i]) {
        signature[i] = h;
      }
    }
  }

  return signature.map(val => (val === Infinity ? 0 : val));
}

/**
 * Estimates Jaccard similarity between two MinHash signature vectors.
 */
export function estimateJaccardSimilarityFromMinHash(
  signatureA: number[],
  signatureB: number[]
): number {
  if (signatureA.length !== signatureB.length || signatureA.length === 0) {
    return 0;
  }

  let matches = 0;
  for (let i = 0; i < signatureA.length; i++) {
    if (signatureA[i] === signatureB[i]) {
      matches++;
    }
  }

  return matches / signatureA.length;
}

/**
 * Compares two raw text documents using MinHash fingerprinting.
 */
export function compareDocumentsMinHash(
  docA: string,
  docB: string,
  nGramSize = 3,
  numPermutations = 64,
  similarityThreshold = 0.45
): MinHashComparisonResult {
  const nGramsA = new Set(generateNGramTokens(docA, nGramSize));
  const nGramsB = generateNGramTokens(docB, nGramSize);

  let exactOverlap = 0;
  for (const token of nGramsB) {
    if (nGramsA.has(token)) {
      exactOverlap++;
    }
  }

  const sigA = computeMinHashSignature(docA, nGramSize, numPermutations);
  const sigB = computeMinHashSignature(docB, nGramSize, numPermutations);

  const estimatedJaccardSimilarity = estimateJaccardSimilarityFromMinHash(sigA, sigB);
  const isPlagiarismCandidate = estimatedJaccardSimilarity >= similarityThreshold;

  return {
    estimatedJaccardSimilarity,
    exactNGramOverlapCount: exactOverlap,
    signatureLength: numPermutations,
    nGramSize,
    isPlagiarismCandidate,
  };
}
