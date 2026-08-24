import { describe, it, expect } from 'vitest';
import { StylometricRadarChartTransformer } from './StylometricRadarChartTransformer';

describe('StylometricRadarChartTransformer', () => {
  it('should transform stylometric vector into radar chart metrics', () => {
    const vector = {
      totalWords: 100,
      totalSentences: 5,
      meanSentenceLength: 20,
      typeTokenRatio: 0.8,
      yulesKMetric: 45,
      fleschKincaidReadingEase: 60,
      punctuationFrequency: new Map(),
      functionWordFrequency: new Map()
    };

    const radar = StylometricRadarChartTransformer.transformToRadarSeries(vector);
    expect(radar.length).toBe(4);
    expect(radar[1].value).toBe(80);
  });
});
