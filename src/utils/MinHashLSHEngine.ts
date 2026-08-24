/**
 * MinHash & Locality-Sensitive Hashing (LSH) Document Fingerprinting Engine.
 * Provides high-throughput k-shingle extraction, min-wise independent hashing,
 * signature matrix generation, band-bucket LSH indexing, and Jaccard similarity estimation.
 */

export interface MinHashConfig {
  numPermutations: number;
  shingleSize: number;
  numBands: number;
  rowsPerBand: number;
  primeModulo: number;
}

export interface DocumentFingerprint {
  docId: string;
  shingleCount: number;
  signature: number[];
  createdAt: string;
}

export interface LSHCandidatePair {
  docIdA: string;
  docIdB: string;
  estimatedJaccard: number;
  bandMatches: number;
}

export class MinHashLSHEngine {
  private config: MinHashConfig;
  private hashCoefficientsA: number[];
  private hashCoefficientsB: number[];
  private lshIndex: Map<string, Set<string>>;
  private fingerprintStore: Map<string, DocumentFingerprint>;

  constructor(config?: Partial<MinHashConfig>) {
    this.config = {
      numPermutations: config?.numPermutations || 128,
      shingleSize: config?.shingleSize || 5,
      numBands: config?.numBands || 16,
      rowsPerBand: config?.rowsPerBand || 8,
      primeModulo: config?.primeModulo || 2147483647
    };

    if (this.config.numBands * this.config.rowsPerBand !== this.config.numPermutations) {
      this.config.numPermutations = this.config.numBands * this.config.rowsPerBand;
    }

    this.hashCoefficientsA = [];
    this.hashCoefficientsB = [];
    this.lshIndex = new Map();
    this.fingerprintStore = new Map();
    this.generateHashFunctions();
  }

  private generateHashFunctions(): void {
    const p = this.config.primeModulo;
    for (let i = 0; i < this.config.numPermutations; i++) {
      const a = (Math.floor(Math.random() * (p - 1)) + 1) | 0;
      const b = Math.floor(Math.random() * p) | 0;
      this.hashCoefficientsA.push(a);
      this.hashCoefficientsB.push(b);
    }
  }

  public extractShingles(text: String): Set<number> {
    const cleanText = text.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ');
    const tokens = cleanText.split(' ');
    const shingles = new Set<number>();
    const k = this.config.shingleSize;

    if (tokens.length < k) {
      shingles.add(this.hashString(cleanText));
      return shingles;
    }

    for (let i = 0; i <= tokens.length - k; i++) {
      const shingleStr = tokens.slice(i, i + k).join(' ');
      shingles.add(this.hashString(shingleStr));
    }

    return shingles;
  }

  private hashString(str: string): number {
    let hash = 5381;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) + hash) + str.charCodeAt(i);
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

  public computeMinHashSignature(shingles: Set<number>): number[] {
    const signature: number[] = new Array(this.config.numPermutations).fill(Infinity);
    const p = this.config.primeModulo;

    shingles.forEach((shingleHash) => {
      for (let i = 0; i < this.config.numPermutations; i++) {
        const a = this.hashCoefficientsA[i];
        const b = this.hashCoefficientsB[i];
        const permutedHash = (a * shingleHash + b) % p;
        if (permutedHash < signature[i]) {
          signature[i] = permutedHash;
        }
      }
    });

    return signature;
  }

  public indexDocument(docId: string, text: string): DocumentFingerprint {
    const shingles = this.extractShingles(text);
    const signature = this.computeMinHashSignature(shingles);

    const fingerprint: DocumentFingerprint = {
      docId,
      shingleCount: shingles.size,
      signature,
      createdAt: new Date().toISOString()
    };

    this.fingerprintStore.set(docId, fingerprint);
    this.insertIntoLSH(docId, signature);
    return fingerprint;
  }

  private insertIntoLSH(docId: string, signature: number[]): void {
    const numBands = this.config.numBands;
    const r = this.config.rowsPerBand;

    for (let b = 0; b < numBands; b++) {
      const bandSlice = signature.slice(b * r, (b + 1) * r);
      const bucketKey = `b${b}:${this.hashString(bandSlice.join(','))}`;

      if (!this.lshIndex.has(bucketKey)) {
        this.lshIndex.set(bucketKey, new Set());
      }
      this.lshIndex.get(bucketKey)!.add(docId);
    }
  }

  public findCandidatePairs(): LSHCandidatePair[] {
    const candidateMatches = new Map<string, number>();

    this.lshIndex.forEach((bucketDocs) => {
      if (bucketDocs.size > 1) {
        const docs = Array.from(bucketDocs);
        for (let i = 0; i < docs.length; i++) {
          for (let j = i + 1; j < docs.length; j++) {
            const pairKey = docs[i] < docs[j] ? `${docs[i]}||${docs[j]}` : `${docs[j]}||${docs[i]}`;
            candidateMatches.set(pairKey, (candidateMatches.get(pairKey) || 0) + 1);
          }
        }
      }
    });

    const candidatePairs: LSHCandidatePair[] = [];
    candidateMatches.forEach((bandMatches, pairKey) => {
      const [docIdA, docIdB] = pairKey.split('||');
      const sigA = this.fingerprintStore.get(docIdA)?.signature;
      const sigB = this.fingerprintStore.get(docIdB)?.signature;

      if (sigA && sigB) {
        const estimatedJaccard = this.estimateJaccard(sigA, sigB);
        candidatePairs.push({
          docIdA,
          docIdB,
          estimatedJaccard,
          bandMatches
        });
      }
    });

    return candidatePairs.sort((a, b) => b.estimatedJaccard - a.estimatedJaccard);
  }

  public estimateJaccard(sigA: number[], sigB: number[]): number {
    if (sigA.length !== sigB.length) return 0;
    let matches = 0;
    for (let i = 0; i < sigA.length; i++) {
      if (sigA[i] === sigB[i]) matches++;
    }
    return matches / sigA.length;
  }

  public getFingerprint(docId: string): DocumentFingerprint | undefined {
    return this.fingerprintStore.get(docId);
  }
}
