export type PolicyStatus = "draft" | "in_review" | "approved" | "retired";

export interface Policy {
  id: number;
  title: string;
  description: string | null;
  status: PolicyStatus;
  version: number;
  owner_id: number | null;
  effective_date: string | null;
  next_review_date: string | null;
  /** Whether employees can read it (once approved) on their home page. */
  shared_with_employees: boolean;
  created_at: string;
  updated_at: string;
}

export interface PolicyHistoryEntry {
  action: string;
  actor_id: number | null;
  timestamp: string;
  diff: Record<string, unknown> | null;
}

export interface PolicyCreateInput {
  title: string;
  description?: string | null;
  owner_id?: number | null;
  effective_date?: string | null;
}

export interface PolicyUpdateInput {
  title?: string;
  description?: string | null;
  owner_id?: number | null;
  effective_date?: string | null;
}
