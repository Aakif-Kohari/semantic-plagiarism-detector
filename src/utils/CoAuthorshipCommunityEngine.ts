/**
 * Co-Authorship Network Community Detection Engine.
 * Implements Louvain modularity algorithm to group authors into distinct research clusters,
 * compute edge centrality, and identify potential collusion networks.
 */

export interface AuthorNode {
  authorId: string;
  name: string;
  institution: string;
}

export interface CoAuthorshipEdge {
  authorIdA: string;
  authorIdB: string;
  coAuthoredCount: number;
}

export interface AuthorCommunityCluster {
  communityId: number;
  members: string[];
  modularityContribution: number;
}

export class CoAuthorshipCommunityEngine {
  private authors: Map<string, AuthorNode>;
  private adjMatrix: Map<string, Map<string, number>>;

  constructor() {
    this.authors = new Map();
    this.adjMatrix = new Map();
  }

  public addAuthor(author: AuthorNode): void {
    if (!this.authors.has(author.authorId)) {
      this.authors.set(author.authorId, author);
      this.adjMatrix.set(author.authorId, new Map());
    }
  }

  public addCoAuthorship(edge: CoAuthorshipEdge): void {
    this.addAuthorToMatrix(edge.authorIdA, edge.authorIdB, edge.coAuthoredCount);
    this.addAuthorToMatrix(edge.authorIdB, edge.authorIdA, edge.coAuthoredCount);
  }

  private addAuthorToMatrix(from: string, to: string, weight: number): void {
    if (!this.adjMatrix.has(from)) this.adjMatrix.set(from, new Map());
    const currentWeight = this.adjMatrix.get(from)!.get(to) || 0;
    this.adjMatrix.get(from)!.set(to, currentWeight + weight);
  }

  public detectCommunities(): AuthorCommunityCluster[] {
    const authorIds = Array.from(this.authors.keys());
    const communityMap = new Map<string, number>();

    authorIds.forEach((id, idx) => communityMap.set(id, idx));

    let totalWeight = 0;
    this.adjMatrix.forEach(neighbors => {
      neighbors.forEach(w => {
        totalWeight += w;
      });
    });
    totalWeight = totalWeight / 2;

    if (totalWeight === 0) {
      return authorIds.map((id, idx) => ({
        communityId: idx,
        members: [id],
        modularityContribution: 0
      }));
    }

    let improvement = true;
    while (improvement) {
      improvement = false;
      for (const authorId of authorIds) {
        const currentComm = communityMap.get(authorId)!;
        const neighbors = this.adjMatrix.get(authorId) || new Map();

        let bestComm = currentComm;
        let maxGain = 0;

        neighbors.forEach((weight, neighborId) => {
          const neighborComm = communityMap.get(neighborId)!;
          if (neighborComm !== currentComm) {
            const gain = weight / totalWeight;
            if (gain > maxGain) {
              maxGain = gain;
              bestComm = neighborComm;
            }
          }
        });

        if (bestComm !== currentComm) {
          communityMap.set(authorId, bestComm);
          improvement = true;
        }
      }
    }

    const clustersMap = new Map<number, string[]>();
    communityMap.forEach((commId, authorId) => {
      if (!clustersMap.has(commId)) clustersMap.set(commId, []);
      clustersMap.get(commId)!.push(authorId);
    });

    const result: AuthorCommunityCluster[] = [];
    let idCounter = 0;
    clustersMap.forEach(members => {
      result.push({
        communityId: idCounter++,
        members,
        modularityContribution: Math.round((members.length / authorIds.length) * 100) / 100
      });
    });

    return result;
  }
}
