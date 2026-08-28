import type { FrameworkControl } from "../framework-controls/types";

export type ImpactAssessmentStatus = "draft" | "completed";

export interface ImpactFactorAssessment {
  id: number;
  factor: string;
  benefits: string | null;
  harms: string | null;
  criteria: string | null;
  score: number | null;
}

export interface ImpactAssessment {
  id: number;
  ai_system_row_id: number;
  status: ImpactAssessmentStatus;
  assessor_id: number | null;
  assessment_date: string | null;
  system_description: string | null;
  intended_purpose: string | null;
  foreseeable_misuse: string | null;
  data_and_model_info: string | null;
  deployment_environment: string | null;
  affected_interested_parties: string | null;
  human_oversight_role: string | null;
  conclusion: string | null;
  created_at: string;
  updated_at: string;
  framework_tags: FrameworkControl[];
  factors: ImpactFactorAssessment[];
}

export interface ImpactAssessmentCreateInput {
  assessor_id?: number | null;
  assessment_date?: string | null;
}

export interface ImpactAssessmentUpdateInput {
  status?: ImpactAssessmentStatus;
  assessor_id?: number | null;
  assessment_date?: string | null;
  system_description?: string | null;
  intended_purpose?: string | null;
  foreseeable_misuse?: string | null;
  data_and_model_info?: string | null;
  deployment_environment?: string | null;
  affected_interested_parties?: string | null;
  human_oversight_role?: string | null;
  conclusion?: string | null;
}

export interface ImpactFactorUpdateInput {
  benefits?: string | null;
  harms?: string | null;
  criteria?: string | null;
  score?: number | null;
}
