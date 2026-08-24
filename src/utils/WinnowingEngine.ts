/**
 * Winnowing Fingerprint Engine.
 * Implements local document fingerprinting using rolling hash (Rabin-Karp style)
 * and sliding window selection to guarantee detection of shared substrings >= threshold.
 */

export interface WinnowingConfig {
  kgramSize: number;
  windowSize: number;
  primeBase: number;
  modulus: number;
}

export interface WinnowedFingerprint {
  hash: number;
  position: number;
}

export class WinnowingEngine {
  private config: WinnowingConfig;

  constructor(config?: Partial<WinnowingConfig>) {
    this.config = {
      kgramSize: config?.kgramSize || 8,
      windowSize: config?.windowSize || 4,
      primeBase: config?.primeBase || 31,
      modulus: config?.modulus || 1000000007
    };
  }

  public sanitizeText(text: string): string {
    return text.toLowerCase().replace(/[^\w]/g, '');
  }

  public computeKgramHashes(sanitizedText: string): { hash: number; pos: number }[] {
    const k = this.config.kgramSize;
    const b = this.config.primeBase;
    const m = this.config.modulus;
    const n = sanitizedText.length;

    if (n < k) return [];

    const hashes: { hash: number; pos: number }[] = [];
    let currentHash = 0;
    let bPowerK = 1;

    for (let i = 0; i < k - 1; i++) {
      bPowerK = (bPowerK * b) % m;
    }

    for (let i = 0; i < k; i++) {
      currentHash = (currentHash * b + sanitizedText.charCodeAt(i)) % m;
    }
    hashes.push({ hash: currentHash, pos: 0 });

    for (let i = 1; i <= n - k; i++) {
      const prevChar = sanitizedText.charCodeAt(i - 1);
      const nextChar = sanitizedText.charCodeAt(i + k - 1);

      currentHash = (currentHash - (prevChar * bPowerK) % m + m) % m;
      currentHash = (currentHash * b + nextChar) % m;
      hashes.push({ hash: currentHash, pos: i });
    }

    return hashes;
  }

  public winnow(text: string): WinnowedFingerprint[] {
    const sanitized = this.sanitizeText(text);
    const kgramHashes = this.computeKgramHashes(sanitized);
    const w = this.config.windowSize;

    if (kgramHashes.length < w) {
      if (kgramHashes.length === 0) return [];
      let minHash = kgramHashes[0];
      for (let i = 1; i < kgramHashes.length; i++) {
        if (kgramHashes[i].hash <= minHash.hash) {
          minHash = kgramHashes[i];
        }
      }
      return [{ hash: minHash.hash, position: minHash.pos }];
    }

    const fingerprints: WinnowedFingerprint[] = [];
    let lastSelectedPos = -1;

    for (let i = 0; i <= kgramHashes.length - w; i++) {
      const window = kgramHashes.slice(i, i + w);
      let minInWindow = window[0];

      for (let j = 1; j < window.length; j++) {
        if (window[j].hash <= minInWindow.hash) {
          minInWindow = window[j];
        }
      }

      if (minInWindow.pos !== lastSelectedPos) {
        fingerprints.push({ hash: minInWindow.hash, position: minInWindow.pos });
        lastSelectedPos = minInWindow.pos;
      }
    }

    return fingerprints;
  }

  public computeContainmentScore(fpDocA: WinnowedFingerprint[], fpDocB: WinnowedFingerprint[]): number {
    if (fpDocA.length === 0 || fpDocB.length === 0) return 0;
    const setB = new Set(fpDocB.map(f => f.hash));
    let matches = 0;
    fpDocA.forEach(f => {
      if (setB.has(f.hash)) matches++;
    });
    return matches / fpDocA.length;
  }
}
