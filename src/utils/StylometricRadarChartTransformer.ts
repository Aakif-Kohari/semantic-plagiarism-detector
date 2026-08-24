/**
 * Stylometric Radar Chart Visualizer Data Transformer.
 * Converts stylometric feature vectors into Radar Chart data formats for UI rendering.
 */

import { StylometricVector } from './MultilingualStylometricExtractor';

export interface RadarMetricPoint {
  axis: string;
  value: number;
}

export class StylometricRadarChartTransformer {
  public static transformToRadarSeries(vector: StylometricVector): RadarMetricPoint[] {
    return [
      { axis: 'Mean Sentence Length', value: Math.min(100, vector.meanSentenceLength * 2) },
      { axis: 'Type-Token Ratio', value: Math.round(vector.typeTokenRatio * 100) },
      { axis: 'Yule\'s K Metric', value: Math.min(100, vector.yulesKMetric) },
      { axis: 'Flesch-Kincaid Ease', value: Math.max(0, Math.min(100, vector.fleschKincaidReadingEase)) }
    ];
  }
}
