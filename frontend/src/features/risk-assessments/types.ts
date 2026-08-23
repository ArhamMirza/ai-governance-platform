import type { MatrixCell } from "./components/RiskMatrix";
import type { RiskCriteria } from "./riskSeverity";

export type RiskAssessmentStatus = "draft" | "in_progress" | "completed";

export interface RiskAssessment {
  id: number;
  ai_system_row_id: number;
  sheet_id: number;
  framework_tags: string[];
  status: RiskAssessmentStatus;
  assessor_id: number | null;
  assessment_date: string | null;
  overall_risk_rating: number | null;
  created_at: string;
  updated_at: string;
}

export interface RiskAssessmentCreateInput {
  ai_system_row_id: number;
  framework_tags?: string[];
  assessor_id?: number | null;
  assessment_date?: string | null;
}

export interface RiskAssessmentUpdateInput {
  framework_tags?: string[];
  status?: RiskAssessmentStatus;
  assessor_id?: number | null;
  assessment_date?: string | null;
}

export interface RiskItemSummary {
  total: number;
  by_severity: Record<string, number>;
  overdue_count: number;
  untreated_count: number;
  average_inherent_score: number | null;
  average_residual_score: number | null;
}

export interface RiskAssessmentStats {
  id: number;
  ai_system_row_id: number;
  status: RiskAssessmentStatus;
  overall_risk_rating: number | null;
  item_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  overdue_count: number;
}

export interface RiskPortfolioSummary {
  total_assessments: number;
  by_status: Record<string, number>;
  high_risk_count: number;
  risk_items: RiskItemSummary;
  matrix: MatrixCell[];
  assessments: RiskAssessmentStats[];
  criteria: RiskCriteria;
}
