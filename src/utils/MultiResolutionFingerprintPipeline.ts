/**
 * Multi-Resolution Document Fingerprinting Pipeline.
 * Orchestrates MinHash LSH global screening and Winnowing local match verification.
 */

import { MinHashLSHEngine, LSHCandidatePair } from './MinHashLSHEngine';
import { WinnowingEngine, WinnowedFingerprint } from './WinnowingEngine';

export interface FingerprintingReport {
  docIdA: string;
  docIdB: string;
  estimatedJaccard: number;
  containmentScore: number;
  isPlagiarismSuspected: boolean;
  timestamp: string;
}

export class MultiResolutionFingerprintPipeline {
  private minHashEngine: MinHashLSHEngine;
  private winnowingEngine: WinnowingEngine;
  private rawDocStore: Map<string, string>;
  private winnowedFpStore: Map<string, WinnowedFingerprint[]>;

  constructor() {
    this.minHashEngine = new MinHashLSHEngine();
    this.winnowingEngine = new WinnowingEngine();
    this.rawDocStore = new Map();
    this.winnowedFpStore = new Map();
  }

  public registerDocument(docId: string, content: string): void {
    this.rawDocStore.set(docId, content);
    this.minHashEngine.indexDocument(docId, content);
    const winnowedFp = this.winnowingEngine.winnow(content);
    this.winnowedFpStore.set(docId, winnowedFp);
  }

  public runPlagiarismAudit(threshold: number = 0.5): FingerprintingReport[] {
    const candidatePairs: LSHCandidatePair[] = this.minHashEngine.findCandidatePairs();
    const reports: FingerprintingReport[] = [];

    candidatePairs.forEach((pair) => {
      const fpA = this.winnowedFpStore.get(pair.docIdA) || [];
      const fpB = this.winnowedFpStore.get(pair.docIdB) || [];

      const containmentScore = this.winnowingEngine.computeContainmentScore(fpA, fpB);
      const isPlagiarismSuspected = pair.estimatedJaccard >= threshold || containmentScore >= threshold;

      reports.push({
        docIdA: pair.docIdA,
        docIdB: pair.docIdB,
        estimatedJaccard: pair.estimatedJaccard,
        containmentScore,
        isPlagiarismSuspected,
        timestamp: new Date().toISOString()
      });
    });

    return reports;
  }
}
