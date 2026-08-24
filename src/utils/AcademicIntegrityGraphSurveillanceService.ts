/**
 * Academic Integrity Graph Surveillance Service.
 * Combines Citation PageRank, Circular Citation Loop Detection, and Co-Authorship Collusion Ring Clustering.
 */

import { CitationNetworkGraphEngine, PageRankResult, CircularCitationCycle } from './CitationNetworkGraphEngine';
import { CoAuthorshipCommunityEngine, AuthorCommunityCluster } from './CoAuthorshipCommunityEngine';

export interface GraphSurveillanceAuditReport {
  topInfluentialPapers: PageRankResult[];
  circularCitationRings: CircularCitationCycle[];
  suspectedCollusionClusters: AuthorCommunityCluster[];
  integrityRiskScore: number;
  timestamp: string;
}

export class AcademicIntegrityGraphSurveillanceService {
  private citationGraph: CitationNetworkGraphEngine;
  private authorshipEngine: CoAuthorshipCommunityEngine;

  constructor() {
    this.citationGraph = new CitationNetworkGraphEngine();
    this.authorshipEngine = new CoAuthorshipCommunityEngine();
  }

  public getCitationGraph(): CitationNetworkGraphEngine {
    return this.citationGraph;
  }

  public getAuthorshipEngine(): CoAuthorshipCommunityEngine {
    return this.authorshipEngine;
  }

  public generateFullAuditReport(): GraphSurveillanceAuditReport {
    const topInfluentialPapers = this.citationGraph.computePageRank();
    const circularCitationRings = this.citationGraph.detectCircularCitations();
    const suspectedCollusionClusters = this.authorshipEngine.detectCommunities();

    let riskScore = 0;
    if (circularCitationRings.length > 0) riskScore += 40;
    if (suspectedCollusionClusters.some(c => c.members.length > 5)) riskScore += 30;

    return {
      topInfluentialPapers: topInfluentialPapers.slice(0, 5),
      circularCitationRings,
      suspectedCollusionClusters,
      integrityRiskScore: Math.min(100, riskScore),
      timestamp: new Date().toISOString()
    };
  }
}
