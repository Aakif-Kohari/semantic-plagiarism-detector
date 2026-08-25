/**
 * Stylometric Author Profiling Engine
 * Extracts stylistic metrics (lexical richness, sentence length distribution, function word frequencies, punctuation density)
 * to profile author signatures and calculate stylometric distance/authorship verification.
 */

export interface StylometricProfile {
  totalWords: number;
  totalSentences: number;
  averageSentenceLength: number;
  typeTokenRatio: number; // Lexical diversity (unique words / total words)
  hapaxLegomenaRatio: number; // Words appearing exactly once / total unique words
  punctuationDensity: number;
  uppercaseWordRatio: number;
  functionWordFrequencies: Record<string, number>;
}

export interface AuthorshipVerificationResult {
  isSameAuthor: boolean;
  authorshipProbability: number;
  stylometricDistance: number;
  profileA: StylometricProfile;
  profileB: StylometricProfile;
  contributingFactors: Array<{ metric: string; difference: number }>;
}

const COMMON_FUNCTION_WORDS = new Set([
  'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
  'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
  'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
  'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what'
]);

/**
 * Extracts fine-grained stylometric metrics from raw text.
 */
export function extractStylometricProfile(text: string): StylometricProfile {
  const words = text.toLowerCase().match(/\b[a-z']+\b/g) || [];
  const rawWords = text.match(/\b[A-Za-z']+\b/g) || [];
  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
  const punctuationCount = (text.match(/[,;:\-"'()]/g) || []).length;

  const totalWords = words.length;
  const totalSentences = Math.max(1, sentences.length);
  const averageSentenceLength = totalWords / totalSentences;

  const wordFrequencyMap: Record<string, number> = {};
  let hapaxCount = 0;

  for (const word of words) {
    wordFrequencyMap[word] = (wordFrequencyMap[word] || 0) + 1;
  }

  const uniqueWords = Object.keys(wordFrequencyMap).length;
  for (const count of Object.values(wordFrequencyMap)) {
    if (count === 1) hapaxCount++;
  }

  const typeTokenRatio = totalWords > 0 ? uniqueWords / totalWords : 0;
  const hapaxLegomenaRatio = uniqueWords > 0 ? hapaxCount / uniqueWords : 0;
  const punctuationDensity = totalWords > 0 ? punctuationCount / totalWords : 0;

  const uppercaseCount = rawWords.filter(w => /^[A-Z]+$/.test(w)).length;
  const uppercaseWordRatio = totalWords > 0 ? uppercaseCount / totalWords : 0;

  const functionWordFrequencies: Record<string, number> = {};
  for (const funcWord of COMMON_FUNCTION_WORDS) {
    const freq = wordFrequencyMap[funcWord] || 0;
    functionWordFrequencies[funcWord] = totalWords > 0 ? freq / totalWords : 0;
  }

  return {
    totalWords,
    totalSentences,
    averageSentenceLength,
    typeTokenRatio,
    hapaxLegomenaRatio,
    punctuationDensity,
    uppercaseWordRatio,
    functionWordFrequencies,
  };
}

/**
 * Calculates normalized Euclidean/Manhattan distance between two stylometric profiles.
 */
export function calculateStylometricDistance(
  profileA: StylometricProfile,
  profileB: StylometricProfile
): number {
  const avgSentenceDiff = Math.abs(profileA.averageSentenceLength - profileB.averageSentenceLength) / 50.0;
  const ttrDiff = Math.abs(profileA.typeTokenRatio - profileB.typeTokenRatio);
  const hapaxDiff = Math.abs(profileA.hapaxLegomenaRatio - profileB.hapaxLegomenaRatio);
  const punctDiff = Math.abs(profileA.punctuationDensity - profileB.punctuationDensity);

  let funcWordDiffSum = 0;
  for (const word of COMMON_FUNCTION_WORDS) {
    const freqA = profileA.functionWordFrequencies[word] || 0;
    const freqB = profileB.functionWordFrequencies[word] || 0;
    funcWordDiffSum += Math.abs(freqA - freqB);
  }
  const avgFuncWordDiff = funcWordDiffSum / COMMON_FUNCTION_WORDS.size;

  const compositeDistance = (
    0.3 * Math.min(1.0, avgSentenceDiff) +
    0.25 * ttrDiff +
    0.2 * hapaxDiff +
    0.15 * Math.min(1.0, punctDiff * 5.0) +
    0.1 * Math.min(1.0, avgFuncWordDiff * 10.0)
  );

  return Math.min(1.0, Math.max(0.0, compositeDistance));
}

/**
 * Performs full authorship verification on two input text samples.
 */
export function verifyAuthorshipMatch(
  textA: string,
  textB: string,
  distanceThreshold = 0.35
): AuthorshipVerificationResult {
  const profileA = extractStylometricProfile(textA);
  const profileB = extractStylometricProfile(textB);

  const stylometricDistance = calculateStylometricDistance(profileA, profileB);
  const authorshipProbability = Math.max(0.0, 1.0 - stylometricDistance);
  const isSameAuthor = stylometricDistance <= distanceThreshold;

  const contributingFactors = [
    { metric: 'Sentence Length Delta', difference: Math.abs(profileA.averageSentenceLength - profileB.averageSentenceLength) },
    { metric: 'Type-Token Ratio Delta', difference: Math.abs(profileA.typeTokenRatio - profileB.typeTokenRatio) },
    { metric: 'Hapax Legomena Delta', difference: Math.abs(profileA.hapaxLegomenaRatio - profileB.hapaxLegomenaRatio) },
    { metric: 'Punctuation Density Delta', difference: Math.abs(profileA.punctuationDensity - profileB.punctuationDensity) },
  ];

  return {
    isSameAuthor,
    authorshipProbability,
    stylometricDistance,
    profileA,
    profileB,
    contributingFactors,
  };
}
