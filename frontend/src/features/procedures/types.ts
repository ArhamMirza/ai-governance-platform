export type ProcedureStatus = "draft" | "in_review" | "approved" | "retired";

export interface Procedure {
  id: number;
  title: string;
  description: string | null;
  status: ProcedureStatus;
  version: number;
  owner_id: number | null;
  policy_id: number | null;
  effective_date: string | null;
  next_review_date: string | null;
  /** Whether employees can read it (once approved) on their home page. */
  shared_with_employees: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProcedureHistoryEntry {
  action: string;
  actor_id: number | null;
  timestamp: string;
  diff: Record<string, unknown> | null;
}

export interface ProcedureCreateInput {
  title: string;
  description?: string | null;
  owner_id?: number | null;
  policy_id?: number | null;
  effective_date?: string | null;
}

export interface ProcedureUpdateInput {
  title?: string;
  description?: string | null;
  owner_id?: number | null;
  policy_id?: number | null;
  effective_date?: string | null;
}
