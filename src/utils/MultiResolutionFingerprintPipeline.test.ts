import { describe, it, expect } from 'vitest';
import { MultiResolutionFingerprintPipeline } from './MultiResolutionFingerprintPipeline';

describe('MultiResolutionFingerprintPipeline', () => {
  it('should run full end-to-end plagiarism audit', () => {
    const pipeline = new MultiResolutionFingerprintPipeline();
    const doc1 = "Artificial intelligence models rely heavily on transformer architectures and multi-head self-attention mechanisms for complex natural language processing tasks.";
    const doc2 = "Artificial intelligence models rely heavily on transformer architectures and multi-head self-attention mechanisms for complex natural language processing tasks with extra commentary attached.";

    pipeline.registerDocument("doc1", doc1);
    pipeline.registerDocument("doc2", doc2);

    const reports = pipeline.runPlagiarismAudit(0.2);
    expect(reports.length).toBeGreaterThanOrEqual(1);
    expect(reports[0].isPlagiarismSuspected).toBe(true);
  });
});
