import { describe, it, expect } from 'vitest';
import { AcademicIntegrityGraphSurveillanceService } from './AcademicIntegrityGraphSurveillanceService';

describe('AcademicIntegrityGraphSurveillanceService', () => {
  it('should generate audit report with risk score evaluation', () => {
    const service = new AcademicIntegrityGraphSurveillanceService();
    const citation = service.getCitationGraph();
    citation.addNode({ id: 'P1', title: 'Paper 1', author: 'A1', year: 2020 });
    citation.addNode({ id: 'P2', title: 'Paper 2', author: 'A2', year: 2021 });
    citation.addEdge({ sourceId: 'P1', targetId: 'P2', weight: 1.0 });

    const report = service.generateFullAuditReport();
    expect(report.topInfluentialPapers.length).toBe(2);
    expect(report.integrityRiskScore).toBeGreaterThanOrEqual(0);
  });
});
