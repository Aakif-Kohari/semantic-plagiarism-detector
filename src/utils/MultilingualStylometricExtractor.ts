/**
 * Multilingual Stylometric Feature Extractor Engine.
 * Extracts sentence length distributions, lexical diversity metrics (TTR, Yule's K),
 * punctuation frequencies, function word usage vectors, and readability indices (Flesch-Kincaid).
 */

export interface StylometricVector {
  totalWords: number;
  totalSentences: number;
  meanSentenceLength: number;
  typeTokenRatio: number;
  yulesKMetric: number;
  fleschKincaidReadingEase: number;
  punctuationFrequency: Map<string, number>;
  functionWordFrequency: Map<string, number>;
}

export class MultilingualStylometricExtractor {
  private functionWords: Set<string>;

  constructor() {
    this.functionWords = new Set([
      'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'to', 'of',
      'for', 'with', 'as', 'by', 'that', 'this', 'it', 'from', 'or', 'are',
      'be', 'was', 'were', 'been', 'have', 'has', 'had', 'but', 'not', 'what'
    ]);
  }

  public extractVector(text: string): StylometricVector {
    const cleanText = text.trim();
    if (!cleanText) {
      return {
        totalWords: 0,
        totalSentences: 0,
        meanSentenceLength: 0,
        typeTokenRatio: 0,
        yulesKMetric: 0,
        fleschKincaidReadingEase: 0,
        punctuationFrequency: new Map(),
        functionWordFrequency: new Map()
      };
    }

    const sentences = cleanText.split(/[.!?]+/).filter(s => s.trim().length > 0);
    const words = cleanText.toLowerCase().replace(/[^\w\s]/g, '').split(/\s+/).filter(w => w.length > 0);

    const totalWords = words.length;
    const totalSentences = Math.max(1, sentences.length);
    const meanSentenceLength = totalWords / totalSentences;

    const uniqueWords = new Set(words);
    const typeTokenRatio = totalWords > 0 ? uniqueWords.size / totalWords : 0;

    const yulesKMetric = this.calculateYulesK(words);
    const fleschKincaidReadingEase = this.calculateFleschKincaid(totalWords, totalSentences, cleanText);

    const punctuationFrequency = new Map<string, number>();
    const puncMatches = cleanText.match(/[,;:\-\(\)"']/g) || [];
    puncMatches.forEach(p => {
      punctuationFrequency.set(p, (punctuationFrequency.get(p) || 0) + 1);
    });

    const functionWordFrequency = new Map<string, number>();
    words.forEach(w => {
      if (this.functionWords.has(w)) {
        functionWordFrequency.set(w, (functionWordFrequency.get(w) || 0) + 1);
      }
    });

    return {
      totalWords,
      totalSentences,
      meanSentenceLength: Math.round(meanSentenceLength * 100) / 100,
      typeTokenRatio: Math.round(typeTokenRatio * 1000) / 1000,
      yulesKMetric: Math.round(yulesKMetric * 100) / 100,
      fleschKincaidReadingEase: Math.round(fleschKincaidReadingEase * 100) / 100,
      punctuationFrequency,
      functionWordFrequency
    };
  }

  private calculateYulesK(words: string[]): number {
    if (words.length === 0) return 0;
    const freqMap = new Map<string, number>();
    words.forEach(w => freqMap.set(w, (freqMap.get(w) || 0) + 1));

    const m1 = words.length;
    let m2 = 0;
    freqMap.forEach(count => {
      m2 += count * count;
    });

    if (m1 * m1 === 0) return 0;
    return 10000 * (m2 / (m1 * m1));
  }

  private calculateFleschKincaid(totalWords: number, totalSentences: number, text: string): number {
    if (totalWords === 0) return 0;
    const syllables = (text.toLowerCase().match(/[aeiouy]{1,2}/g) || []).length;
    return 206.835 - (1.015 * (totalWords / totalSentences)) - (84.6 * (syllables / totalWords));
  }
}
