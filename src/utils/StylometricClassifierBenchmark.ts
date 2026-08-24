/**
 * Stylometric Classifier Benchmark Utility.
 * Evaluates author classification precision and recall metrics.
 */

export interface BenchmarkMetrics {
  precision: number;
  recall: number;
  f1Score: number;
}

export class StylometricClassifierBenchmark {
  public static calculateF1(truePositives: number, falsePositives: number, falseNegatives: number): BenchmarkMetrics {
    const precision = truePositives + falsePositives > 0 ? truePositives / (truePositives + falsePositives) : 0;
    const recall = truePositives + falseNegatives > 0 ? truePositives / (truePositives + falseNegatives) : 0;
    const f1Score = precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0;

    return {
      precision: Math.round(precision * 1000) / 1000,
      recall: Math.round(recall * 1000) / 1000,
      f1Score: Math.round(f1Score * 1000) / 1000
    };
  }
}
