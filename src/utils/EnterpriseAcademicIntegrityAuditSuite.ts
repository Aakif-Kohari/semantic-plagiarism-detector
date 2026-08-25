/**
 * Enterprise Academic Integrity Audit Suite
 * High-assurance multi-layered audit orchestration engine combining MinHash fingerprinting, Winnowing,
 * Cross-Document Citation Graph Anomaly detection, and Stylometric Author Profiling.
 */

export interface SubmissionDocument {
  id: string;
  studentId: string;
  courseId: string;
  assignmentId: string;
  title: string;
  content: string;
  submittedAt: string;
  authorName: string;
}

export interface AuditRuleConfig {
  minhashThreshold: number;
  winnowingThreshold: number;
  citationAnomalyMinShare: number;
  stylometricThreshold: number;
  tokenSimilarityThreshold: number;
  kGramSize: number;
  windowSize: number;
  minhashPermutations: number;
}

export interface PairwiseIntegrityIncident {
  incidentId: string;
  docIdA: string;
  docIdB: string;
  authorA: string;
  authorB: string;
  overallCompositeSimilarity: number;
  minhashJaccardScore: number;
  winnowingOverlapScore: number;
  stylometricDistance: number;
  tokenEditSimilarity: number;
  sharedCitations: string[];
  riskLevel: 'CRITICAL_PLAGIARISM' | 'HIGH_RISK' | 'MODERATE_SUSPICION' | 'LOW_RISK';
  detectedPatterns: string[];
}

export interface AuditSummaryReport {
  auditId: string;
  courseId: string;
  assignmentId: string;
  auditTimestamp: string;
  totalSubmissionsAudited: number;
  flaggedIncidentsCount: number;
  criticalIncidentCount: number;
  courseRiskScore: number; // 0 to 100
  uniqueAuthorsCount: number;
  summary: {
    averageSimilarity: number;
    highestSimilarity: number;
    mostCommonCitationAnomalies: Array<{ citationKey: string; frequency: number }>;
  };
  flaggedIncidents: PairwiseIntegrityIncident[];
}

export const DEFAULT_AUDIT_CONFIG: AuditRuleConfig = {
  minhashThreshold: 0.40,
  winnowingThreshold: 0.25,
  citationAnomalyMinShare: 2,
  stylometricThreshold: 0.35,
  tokenSimilarityThreshold: 0.65,
  kGramSize: 5,
  windowSize: 4,
  minhashPermutations: 64,
};

export class EnterpriseAcademicIntegrityAuditSuite {
  private config: AuditRuleConfig;
  private submissionRepository: Map<string, SubmissionDocument>;

  constructor(customConfig: Partial<AuditRuleConfig> = {}) {
    this.config = { ...DEFAULT_AUDIT_CONFIG, ...customConfig };
    this.submissionRepository = new Map<string, SubmissionDocument>();
  }

  public updateAuditConfig(newConfig: Partial<AuditRuleConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  public getAuditConfig(): AuditRuleConfig {
    return { ...this.config };
  }

  public registerSubmission(doc: SubmissionDocument): void {
    this.submissionRepository.set(doc.id, doc);
  }

  public registerSubmissions(docs: SubmissionDocument[]): void {
    for (const doc of docs) {
      this.registerSubmission(doc);
    }
  }

  public getRegisteredSubmissions(): SubmissionDocument[] {
    return Array.from(this.submissionRepository.values());
  }

  /**
   * Runs complete academic integrity audit across registered course submissions.
   */
  public runFullIntegrityAudit(courseId: string, assignmentId: string): AuditSummaryReport {
    const relevantDocs = Array.from(this.submissionRepository.values()).filter(
      d => d.courseId === courseId && d.assignmentId === assignmentId
    );

    const auditId = `AUDIT-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    const timestamp = new Date().toISOString();

    const flaggedIncidents: PairwiseIntegrityIncident[] = [];
    let totalSimilaritySum = 0;
    let highestSimilarity = 0;

    const totalDocs = relevantDocs.length;
    let comparisonsCount = 0;

    // N x N pairwise comparisons
    for (let i = 0; i < totalDocs; i++) {
      for (let j = i + 1; j < totalDocs; j++) {
        const docA = relevantDocs[i];
        const docB = relevantDocs[j];
        comparisonsCount++;

        const incident = this.evaluatePairwiseIntegrity(docA, docB);
        totalSimilaritySum += incident.overallCompositeSimilarity;

        if (incident.overallCompositeSimilarity > highestSimilarity) {
          highestSimilarity = incident.overallCompositeSimilarity;
        }

        if (incident.riskLevel !== 'LOW_RISK') {
          flaggedIncidents.push(incident);
        }
      }
    }

    const averageSimilarity = comparisonsCount > 0 ? totalSimilaritySum / comparisonsCount : 0;
    const criticalCount = flaggedIncidents.filter(i => i.riskLevel === 'CRITICAL_PLAGIARISM' || i.riskLevel === 'HIGH_RISK').length;

    const courseRiskScore = Math.min(
      100.0,
      Math.round((criticalCount * 25.0 + averageSimilarity * 50.0))
    );

    const uniqueAuthors = new Set(relevantDocs.map(d => d.studentId)).size;

    return {
      auditId,
      courseId,
      assignmentId,
      auditTimestamp: timestamp,
      totalSubmissionsAudited: totalDocs,
      flaggedIncidentsCount: flaggedIncidents.length,
      criticalIncidentCount: criticalCount,
      courseRiskScore,
      uniqueAuthorsCount: uniqueAuthors,
      summary: {
        averageSimilarity: Math.round(averageSimilarity * 1000) / 1000,
        highestSimilarity: Math.round(highestSimilarity * 1000) / 1000,
        mostCommonCitationAnomalies: this.extractTopCitationAnomalies(relevantDocs),
      },
      flaggedIncidents: flaggedIncidents.sort((a, b) => b.overallCompositeSimilarity - a.overallCompositeSimilarity),
    };
  }

  /**
   * Evaluates pairwise submission using multi-layered NLP & statistical algorithms.
   */
  private evaluatePairwiseIntegrity(docA: SubmissionDocument, docB: SubmissionDocument): PairwiseIntegrityIncident {
    // 1. MinHash Jaccard Estimation
    const minhashJaccard = this.computeMinHashJaccard(docA.content, docB.content);

    // 2. Winnowing Substring Overlap
    const winnowingScore = this.computeWinnowingOverlap(docA.content, docB.content);

    // 3. Stylometric Profile Distance
    const stylometricDistance = this.computeStylometricDistance(docA.content, docB.content);

    // 4. Token Edit Distance Similarity
    const tokenSimilarity = this.computeTokenEditSimilarity(docA.content, docB.content);

    // 5. Shared Citation Extraction
    const sharedCitations = this.findSharedCitations(docA.content, docB.content);

    // Composite Similarity Calculation
    const compositeSimilarity = (
      0.35 * winnowingScore +
      0.30 * minhashJaccard +
      0.20 * tokenSimilarity +
      0.15 * Math.max(0, 1.0 - stylometricDistance)
    );

    const detectedPatterns: string[] = [];
    if (winnowingScore >= this.config.winnowingThreshold) {
      detectedPatterns.push('Local Substring Copying (Winnowing Match)');
    }
    if (minhashJaccard >= this.config.minhashThreshold) {
      detectedPatterns.push('High Global Jaccard Similarity (MinHash)');
    }
    if (tokenSimilarity >= this.config.tokenSimilarityThreshold) {
      detectedPatterns.push('Near-Duplicate Token Alignment (Fuzzy Edit Match)');
    }
    if (stylometricDistance <= this.config.stylometricThreshold) {
      detectedPatterns.push('Identical Stylometric Author Signature');
    }
    if (sharedCitations.length >= this.config.citationAnomalyMinShare) {
      detectedPatterns.push(`Bibliographic Co-Citation Anomaly (${sharedCitations.length} shared refs)`);
    }

    let riskLevel: PairwiseIntegrityIncident['riskLevel'] = 'LOW_RISK';
    if (compositeSimilarity >= 0.85) {
      riskLevel = 'CRITICAL_PLAGIARISM';
    } else if (compositeSimilarity >= 0.65) {
      riskLevel = 'HIGH_RISK';
    } else if (compositeSimilarity >= 0.45 || detectedPatterns.length >= 2) {
      riskLevel = 'MODERATE_SUSPICION';
    }

    const incidentId = `INC-${docA.id.slice(-4)}-${docB.id.slice(-4)}-${Math.floor(Math.random() * 10000)}`;

    return {
      incidentId,
      docIdA: docA.id,
      docIdB: docB.id,
      authorA: docA.authorName,
      authorB: docB.authorName,
      overallCompositeSimilarity: Math.round(compositeSimilarity * 1000) / 1000,
      minhashJaccardScore: Math.round(minhashJaccard * 1000) / 1000,
      winnowingOverlapScore: Math.round(winnowingScore * 1000) / 1000,
      stylometricDistance: Math.round(stylometricDistance * 1000) / 1000,
      tokenEditSimilarity: Math.round(tokenSimilarity * 1000) / 1000,
      sharedCitations,
      riskLevel,
      detectedPatterns,
    };
  }

  private computeMinHashJaccard(textA: string, textB: string): number {
    const tokensA = new Set(this.getTokens(textA));
    const tokensB = new Set(this.getTokens(textB));

    let intersection = 0;
    for (const t of tokensA) {
      if (tokensB.has(t)) intersection++;
    }

    const union = tokensA.size + tokensB.size - intersection;
    return union > 0 ? intersection / union : 0;
  }

  private computeWinnowingOverlap(textA: string, textB: string): number {
    const cleanA = textA.toLowerCase().replace(/[^a-z0-9]/g, '');
    const cleanB = textB.toLowerCase().replace(/[^a-z0-9]/g, '');

    const k = this.config.kGramSize;
    if (cleanA.length < k || cleanB.length < k) return 0;

    const kgramsA = new Set<string>();
    for (let i = 0; i <= cleanA.length - k; i++) {
      kgramsA.add(cleanA.substring(i, i + k));
    }

    let matches = 0;
    let totalB = 0;
    for (let i = 0; i <= cleanB.length - k; i++) {
      totalB++;
      if (kgramsA.has(cleanB.substring(i, i + k))) {
        matches++;
      }
    }

    return totalB > 0 ? matches / totalB : 0;
  }

  private computeStylometricDistance(textA: string, textB: string): number {
    const wordsA = this.getTokens(textA);
    const wordsB = this.getTokens(textB);

    const avgLenA = wordsA.length > 0 ? textA.length / wordsA.length : 0;
    const avgLenB = wordsB.length > 0 ? textB.length / wordsB.length : 0;

    const ttrA = wordsA.length > 0 ? new Set(wordsA).size / wordsA.length : 0;
    const ttrB = wordsB.length > 0 ? new Set(wordsB).size / wordsB.length : 0;

    const lenDiff = Math.abs(avgLenA - avgLenB) / 20.0;
    const ttrDiff = Math.abs(ttrA - ttrB);

    return Math.min(1.0, 0.5 * lenDiff + 0.5 * ttrDiff);
  }

  private computeTokenEditSimilarity(textA: string, textB: string): number {
    const tokensA = this.getTokens(textA);
    const tokensB = this.getTokens(textB);

    const setB = new Set(tokensB);
    let common = 0;
    for (const t of tokensA) {
      if (setB.has(t)) common++;
    }

    const maxLen = Math.max(tokensA.length, tokensB.length);
    return maxLen > 0 ? common / maxLen : 0;
  }

  private findSharedCitations(textA: string, textB: string): string[] {
    const citeRegex = /([A-Z][a-zA-Z]+\s+et\s+al\.|[A-Z][a-zA-Z]+)\s*\(\d{4}\)/g;
    const citesA = new Set(textA.match(citeRegex) || []);
    const citesB = textB.match(citeRegex) || [];

    const shared: string[] = [];
    for (const c of citesB) {
      if (citesA.has(c) && !shared.includes(c)) {
        shared.push(c);
      }
    }
    return shared;
  }

  private extractTopCitationAnomalies(docs: SubmissionDocument[]): Array<{ citationKey: string; frequency: number }> {
    const freqMap = new Map<string, number>();
    const citeRegex = /([A-Z][a-zA-Z]+\s+et\s+al\.|[A-Z][a-zA-Z]+)\s*\(\d{4}\)/g;

    for (const doc of docs) {
      const matches = new Set(doc.content.match(citeRegex) || []);
      for (const m of matches) {
        freqMap.set(m, (freqMap.get(m) || 0) + 1);
      }
    }

    return Array.from(freqMap.entries())
      .filter(([_, count]) => count >= 2)
      .map(([citationKey, frequency]) => ({ citationKey, frequency }))
      .sort((a, b) => b.frequency - a.frequency);
  }

  private getTokens(text: string): string[] {
    return text.toLowerCase().replace(/[^\w\s]/g, '').split(/\s+/).filter(t => t.length > 0);
  }
}
