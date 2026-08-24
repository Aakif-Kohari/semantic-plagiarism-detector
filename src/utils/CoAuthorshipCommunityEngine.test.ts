import { describe, it, expect } from 'vitest';
import { CoAuthorshipCommunityEngine } from './CoAuthorshipCommunityEngine';

describe('CoAuthorshipCommunityEngine', () => {
  it('should group co-authoring researchers into modular communities', () => {
    const engine = new CoAuthorshipCommunityEngine();
    engine.addAuthor({ authorId: 'A1', name: 'Alice', institution: 'MIT' });
    engine.addAuthor({ authorId: 'A2', name: 'Bob', institution: 'MIT' });
    engine.addAuthor({ authorId: 'A3', name: 'Charlie', institution: 'Stanford' });
    engine.addAuthor({ authorId: 'A4', name: 'David', institution: 'Stanford' });

    engine.addCoAuthorship({ authorIdA: 'A1', authorIdB: 'A2', coAuthoredCount: 5 });
    engine.addCoAuthorship({ authorIdA: 'A3', authorIdB: 'A4', coAuthoredCount: 8 });

    const communities = engine.detectCommunities();
    expect(communities.length).toBe(2);
  });
});
