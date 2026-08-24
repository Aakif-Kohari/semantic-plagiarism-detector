/**
 * Locality-Sensitive SimHash Code Clone Detection Engine.
 * Converts normalized AST token streams into 64-bit SimHash vector fingerprints
 * and computes Hamming distances for sub-linear Code Clone detection.
 */

export class SimHashCodeCloneEngine {
  private bitLength: number;

  constructor(bitLength: number = 64) {
    this.bitLength = bitLength;
  }

  private hashToken(token: string): number[] {
    let hash = 5381;
    for (let i = 0; i < token.length; i++) {
      hash = ((hash << 5) + hash) + token.charCodeAt(i);
      hash = hash & hash;
    }

    const bits: number[] = new Array(this.bitLength).fill(0);
    for (let i = 0; i < this.bitLength; i++) {
      bits[i] = (hash & (1 << (i % 31))) !== 0 ? 1 : -1;
    }
    return bits;
  }

  public computeSimHash(tokens: string[]): string {
    const v: number[] = new Array(this.bitLength).fill(0);

    tokens.forEach(token => {
      const tokenBits = this.hashToken(token);
      for (let i = 0; i < this.bitLength; i++) {
        v[i] += tokenBits[i];
      }
    });

    let fingerprint = '';
    for (let i = 0; i < this.bitLength; i++) {
      fingerprint += v[i] > 0 ? '1' : '0';
    }

    return fingerprint;
  }

  public computeHammingDistance(hashA: string, hashB: string): number {
    if (hashA.length !== hashB.length) return this.bitLength;
    let distance = 0;
    for (let i = 0; i < hashA.length; i++) {
      if (hashA[i] !== hashB[i]) distance++;
    }
    return distance;
  }

  public computeSimHashSimilarity(hashA: string, hashB: string): number {
    const distance = this.computeHammingDistance(hashA, hashB);
    return (this.bitLength - distance) / this.bitLength;
  }
}
