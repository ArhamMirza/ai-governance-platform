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
