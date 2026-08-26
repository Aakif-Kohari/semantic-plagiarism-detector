/**
 * Authorship Verification & Ghostwriting Identification Engine.
 * Verifies document authorship against registered author style profiles.
 */

import { MultilingualStylometricExtractor, StylometricVector } from './MultilingualStylometricExtractor';
import { AuthorStylometricDistanceCalculator } from './AuthorStylometricDistanceCalculator';

export interface AuthorProfile {
  authorId: string;
  name: string;
  sampleCount: number;
  centroidVector: StylometricVector;
}

export interface VerificationResult {
  authorId: string;
  authorName: string;
  cosineSimilarity: number;
  euclideanDistance: number;
  isMatch: boolean;
  confidenceScore: number;
}

export class AuthorshipVerificationEngine {
  private extractor: MultilingualStylometricExtractor;
  private calculator: AuthorStylometricDistanceCalculator;
  private profiles: Map<string, AuthorProfile>;

  constructor() {
    this.extractor = new MultilingualStylometricExtractor();
    this.calculator = new AuthorStylometricDistanceCalculator();
    this.profiles = new Map();
  }

  public registerAuthorProfile(authorId: string, name: string, sampleTexts: string[]): AuthorProfile {
    const vectors = sampleTexts.map(t => this.extractor.extractVector(t));
    if (vectors.length === 0) {
      throw new Error("At least one sample text is required to register an author profile.");
    }

    let sumWords = 0;
    let sumSentences = 0;
    let sumMSL = 0;
    let sumTTR = 0;
    let sumYule = 0;
    let sumFlesch = 0;

    vectors.forEach(v => {
      sumWords += v.totalWords;
      sumSentences += v.totalSentences;
      sumMSL += v.meanSentenceLength;
      sumTTR += v.typeTokenRatio;
      sumYule += v.yulesKMetric;
      sumFlesch += v.fleschKincaidReadingEase;
    });

    const count = vectors.length;
    const centroidVector: StylometricVector = {
      totalWords: Math.round(sumWords / count),
      totalSentences: Math.round(sumSentences / count),
      meanSentenceLength: Math.round((sumMSL / count) * 100) / 100,
      typeTokenRatio: Math.round((sumTTR / count) * 1000) / 1000,
      yulesKMetric: Math.round((sumYule / count) * 100) / 100,
      fleschKincaidReadingEase: Math.round((sumFlesch / count) * 100) / 100,
      punctuationFrequency: new Map(),
      functionWordFrequency: new Map()
    };

    const profile: AuthorProfile = {
      authorId,
      name,
      sampleCount: count,
      centroidVector
    };

    this.profiles.set(authorId, profile);
    return profile;
  }

  public verifyAuthorship(unknownText: string, claimedAuthorId: string, threshold: number = 0.85): VerificationResult {
    const profile = this.profiles.get(claimedAuthorId);
    if (!profile) {
      throw new Error(`Author profile ${claimedAuthorId} not found.`);
    }

    const unknownVec = this.extractor.extractVector(unknownText);
    const cosineSimilarity = this.calculator.computeCosineSimilarity(unknownVec, profile.centroidVector);
    const euclideanDistance = this.calculator.computeEuclideanDistance(unknownVec, profile.centroidVector);

    const isMatch = cosineSimilarity >= threshold;
    const confidenceScore = Math.round(cosineSimilarity * 100);

    return {
      authorId: claimedAuthorId,
      authorName: profile.name,
      cosineSimilarity,
      euclideanDistance,
      isMatch,
      confidenceScore
    };
  }
}
