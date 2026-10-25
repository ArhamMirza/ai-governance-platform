import type { ComplianceStatusSummary } from "../compliance-status/types";
import type { MatrixCell } from "../risk-assessments/components/RiskMatrix";
import type { RiskCriteria } from "../risk-assessments/riskSeverity";

export interface StatusCounts {
  total: number;
  by_status: Record<string, number>;
}

export interface AISystemSummary {
  total: number;
  by_risk_tier: Record<string, number>;
}

export interface RiskAssessmentSummary {
  total: number;
  by_status: Record<string, number>;
  high_risk_count: number;
}

export interface RiskItemSummary {
  total: number;
  by_severity: Record<string, number>;
  overdue_count: number;
  untreated_count: number;
  average_inherent_score: number | null;
  average_residual_score: number | null;
}

export interface CoverageSummary {
  ai_systems_total: number;
  ai_systems_assessed: number;
  ai_systems_impact_assessed: number;
  assessments_review_overdue: number;
  policies_total: number;
  policies_approved: number;
  procedures_total: number;
  procedures_approved: number;
}

export interface AttentionItem {
  key: string;
  label: string;
  count: number;
  severity: string;
  /** The area it belongs to. Items arrive ordered so each area's items are
   * contiguous, areas with anything critical first. */
  group: string;
}

export interface MyRiskItem {
  risk_assessment_id: number;
  row_id: number;
  category: string | null;
  description: string | null;
  status: string | null;
  treatment_deadline: string | null;
  overdue: boolean;
}

export interface MyCorrectiveActionItem {
  id: number;
  title: string;
  status: string;
  due_date: string;
  overdue: boolean;
}

export interface MyTrainingItem {
  requirement_id: number;
  title: string;
  status: "expired" | "missing";
  next_due: string | null;
}

export type PendingApprovalEntityType =
  | "Policy"
  | "Procedure"
  | "AISystemDeployment"
  | "AISystemRetirement"
  | "RiskAssessment"
  | "ImpactAssessment"
  | "DataInventory";

export interface PendingApprovalItem {
  entity_type: PendingApprovalEntityType;
  entity_id: number;
  title: string;
  stage_label: string;
  submitted_at: string | null;
}

export interface DashboardSummary {
  policies: StatusCounts;
  procedures: StatusCounts;
  ai_systems: AISystemSummary;
  risk_assessments: RiskAssessmentSummary;
  risk_items: RiskItemSummary;
  coverage: CoverageSummary;
  compliance: ComplianceStatusSummary;
  attention: AttentionItem[];
  matrix: MatrixCell[];
  criteria: RiskCriteria;
  my_risk_items: MyRiskItem[];
  my_corrective_actions: MyCorrectiveActionItem[];
  my_training: MyTrainingItem[];
  pending_approvals: PendingApprovalItem[];
}

/** One thing to do when setting the platform up, and whether the records say it is done. */
export interface GettingStartedStep {
  key: string;
  title: string;
  why: string;
  href: string;
  done: boolean;
  optional: boolean;
}

export interface GettingStarted {
  steps: GettingStartedStep[];
  done_count: number;
  total: number;
  /** Every step that isn't optional is done. */
  complete: boolean;
  /** The first step still to do, in the order a person should take them. */
  next_key: string | null;
}
