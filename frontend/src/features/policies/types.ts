export type PolicyStatus = "draft" | "in_review" | "approved" | "retired";

export interface Policy {
  id: number;
  title: string;
  description: string | null;
  status: PolicyStatus;
  version: number;
  owner_id: number | null;
  content: string;
  effective_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface PolicyVersion {
  id: number;
  policy_id: number;
  version_no: number;
  content: string;
  changed_by: number | null;
  changed_at: string;
  change_note: string | null;
}

export interface PolicyCreateInput {
  title: string;
  description?: string | null;
  content?: string;
  effective_date?: string | null;
}

export interface PolicyUpdateInput {
  title?: string;
  description?: string | null;
  content?: string;
  effective_date?: string | null;
  change_note?: string | null;
}
