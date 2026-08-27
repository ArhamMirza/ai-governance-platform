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

export interface DashboardSummary {
  policies: StatusCounts;
  procedures: StatusCounts;
  ai_systems: AISystemSummary;
  risk_assessments: RiskAssessmentSummary;
  risk_items: RiskItemSummary;
  coverage: CoverageSummary;
  attention: AttentionItem[];
  matrix: MatrixCell[];
  criteria: RiskCriteria;
  my_risk_items: MyRiskItem[];
}
