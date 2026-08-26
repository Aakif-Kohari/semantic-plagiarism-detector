/**
 * Cosine & Euclidean Author Stylometric Distance Calculator.
 * Measures stylistic distances between author profiles and unknown text samples.
 */

import { StylometricVector } from './MultilingualStylometricExtractor';

export class AuthorStylometricDistanceCalculator {

  public computeCosineSimilarity(vecA: StylometricVector, vecB: StylometricVector): number {
    const featuresA = [
      vecA.meanSentenceLength,
      vecA.typeTokenRatio,
      vecA.yulesKMetric,
      vecA.fleschKincaidReadingEase
    ];

    const featuresB = [
      vecB.meanSentenceLength,
      vecB.typeTokenRatio,
      vecB.yulesKMetric,
      vecB.fleschKincaidReadingEase
    ];

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < featuresA.length; i++) {
      dotProduct += featuresA[i] * featuresB[i];
      normA += featuresA[i] * featuresA[i];
      normB += featuresB[i] * featuresB[i];
    }

    if (normA === 0 || normB === 0) return 0;
    const similarity = dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    return Math.round(similarity * 1000) / 1000;
  }

  public computeEuclideanDistance(vecA: StylometricVector, vecB: StylometricVector): number {
    const d1 = vecA.meanSentenceLength - vecB.meanSentenceLength;
    const d2 = (vecA.typeTokenRatio - vecB.typeTokenRatio) * 10;
    const d3 = (vecA.yulesKMetric - vecB.yulesKMetric) / 10;
    const d4 = (vecA.fleschKincaidReadingEase - vecB.fleschKincaidReadingEase) / 10;

    const sumSquare = d1 * d1 + d2 * d2 + d3 * d3 + d4 * d4;
    return Math.round(Math.sqrt(sumSquare) * 100) / 100;
  }
}
