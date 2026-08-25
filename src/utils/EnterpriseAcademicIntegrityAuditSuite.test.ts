import { describe, it, expect, beforeEach } from 'vitest';
import {
  EnterpriseAcademicIntegrityAuditSuite,
  SubmissionDocument,
  AuditRuleConfig,
} from './EnterpriseAcademicIntegrityAuditSuite';

describe('EnterpriseAcademicIntegrityAuditSuite', () => {
  let auditSuite: EnterpriseAcademicIntegrityAuditSuite;

  const doc1: SubmissionDocument = {
    id: 'sub_001',
    studentId: 'student_101',
    courseId: 'CS-401',
    assignmentId: 'ASSIGN-1',
    title: 'Distributed Systems & AI Architecture',
    content: `Distributed computing systems utilize multiple autonomous nodes communicating over high-speed networks to solve complex compute tasks. In their landmark study, Smith et al. (2020) demonstrated deep learning advancements across distributed clusters. Furthermore, neural network architectures continue to evolve at an unprecedented speed, enabling complex pattern recognition and semantic text analysis across diverse domain datasets.`,
    submittedAt: '2026-08-25T10:00:00Z',
    authorName: 'Alice Johnson',
  };

  const doc2: SubmissionDocument = {
    id: 'sub_002',
    studentId: 'student_102',
    courseId: 'CS-401',
    assignmentId: 'ASSIGN-1',
    title: 'Distributed Compute and Deep Learning',
    content: `Distributed computing systems use multiple autonomous nodes communicating over networks to solve compute tasks. Smith et al. (2020) demonstrated deep learning advancements across distributed clusters. Neural network architectures continue to evolve at high speed, enabling complex pattern recognition and text analysis across domain datasets.`,
    submittedAt: '2026-08-25T10:15:00Z',
    authorName: 'Bob Smith',
  };

  const doc3: SubmissionDocument = {
    id: 'sub_003',
    studentId: 'student_103',
    courseId: 'CS-401',
    assignmentId: 'ASSIGN-1',
    title: 'Quantum Entanglement & Supercomputing',
    content: `Quantum computing leverages superposition and entanglement to execute complex calculations faster than classical supercomputers. Brown et al. (2019) introduced key quantum algorithms for cryptography.`,
    submittedAt: '2026-08-25T10:30:00Z',
    authorName: 'Charlie Brown',
  };

  beforeEach(() => {
    auditSuite = new EnterpriseAcademicIntegrityAuditSuite();
  });

  it('should register submission documents into audit repository', () => {
    auditSuite.registerSubmission(doc1);
    auditSuite.registerSubmission(doc2);

    const registered = auditSuite.getRegisteredSubmissions();
    expect(registered.length).toBe(2);
    expect(registered[0].id).toBe('sub_001');
  });

  it('should run comprehensive integrity audit and detect semantic & winnowing matches', () => {
    auditSuite.registerSubmission(doc1);
    auditSuite.registerSubmission(doc2);
    auditSuite.registerSubmission(doc3);

    const report = auditSuite.runFullIntegrityAudit('CS-401', 'ASSIGN-1');

    expect(report).toBeDefined();
    expect(report.totalSubmissionsAudited).toBe(3);
    expect(report.flaggedIncidents.length).toBeGreaterThan(0);

    const flaggedPair = report.flaggedIncidents[0];
    expect(flaggedPair.docIdA).toBe('sub_001');
    expect(flaggedPair.docIdB).toBe('sub_002');
    expect(flaggedPair.riskLevel).toBe('HIGH_RISK');
    expect(flaggedPair.winnowingOverlapScore).toBeGreaterThan(0.3);
  });

  it('should calculate course-level integrity risk score and analytics summary', () => {
    auditSuite.registerSubmission(doc1);
    auditSuite.registerSubmission(doc2);

    const report = auditSuite.runFullIntegrityAudit('CS-401', 'ASSIGN-1');

    expect(report.summary.courseRiskScore).toBeGreaterThan(50);
    expect(report.summary.criticalIncidentCount).toBeGreaterThan(0);
    expect(report.summary.uniqueAuthorsCount).toBe(2);
  });

  it('should allow custom audit rule configuration updates', () => {
    const customConfig: Partial<AuditRuleConfig> = {
      minhashThreshold: 0.8,
      stylometricThreshold: 0.1,
    };

    auditSuite.updateAuditConfig(customConfig);
    const updated = auditSuite.getAuditConfig();

    expect(updated.minhashThreshold).toBe(0.8);
    expect(updated.stylometricThreshold).toBe(0.1);
  });
});
