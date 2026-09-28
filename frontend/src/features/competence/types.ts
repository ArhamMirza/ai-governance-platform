import type { FrameworkControl } from "../framework-controls/types";

export type CompetenceStatus = "current" | "expired" | "missing";

export interface PersonCompetence {
  user_id: number;
  status: CompetenceStatus;
  last_completed_on: string | null;
  next_due: string | null;
}

export interface CompetenceRecord {
  id: number;
  requirement_id: number;
  user_id: number;
  completed_on: string;
  notes: string | null;
  recorded_by: number | null;
  created_at: string;
}

export interface CompetenceRequirementSummary {
  id: number;
  title: string;
  description: string | null;
  /** null = everyone (all active users). */
  governance_role_id: number | null;
  /** null = completing it once is enough. */
  refresh_interval_months: number | null;
  required_count: number;
  current_count: number;
  gap_count: number;
  created_at: string;
  updated_at: string;
}

export interface CompetenceRequirement extends CompetenceRequirementSummary {
  people: PersonCompetence[];
  records: CompetenceRecord[];
  framework_tags: FrameworkControl[];
}

export interface CompetenceRequirementInput {
  title?: string;
  description?: string | null;
  governance_role_id?: number | null;
  refresh_interval_months?: number | null;
}

export interface CompetenceRecordInput {
  user_id: number;
  completed_on: string;
  notes?: string | null;
}
