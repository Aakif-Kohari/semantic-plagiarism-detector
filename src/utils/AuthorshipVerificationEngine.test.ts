import { describe, it, expect } from 'vitest';
import { AuthorshipVerificationEngine } from './AuthorshipVerificationEngine';

describe('AuthorshipVerificationEngine', () => {
  const engine = new AuthorshipVerificationEngine();

  it('should register author profile and verify claimed authorship', () => {
    const samples = [
      "Quantum mechanics explains the behavior of subatomic particles.",
      "Entanglement and superposition are foundational principles of quantum computing."
    ];
    engine.registerAuthorProfile("AUTH-1", "Dr. Feynman", samples);

    const testDoc = "Subatomic particles display wave particle duality under measurement.";
    const result = engine.verifyAuthorship(testDoc, "AUTH-1", 0.70);

    expect(result.authorName).toBe("Dr. Feynman");
    expect(result.confidenceScore).toBeGreaterThan(70);
  });
});
