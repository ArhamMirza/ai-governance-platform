import type { FrameworkControl } from "../framework-controls/types";

export type CorrectiveActionStatus = "open" | "in_progress" | "pending_verification" | "closed";

export interface CorrectiveAction {
  id: number;
  title: string;
  nonconformity_description: string;
  root_cause: string | null;
  action_description: string | null;
  source_type: string | null;
  source_id: number | null;
  assignee_id: number | null;
  due_date: string;
  status: CorrectiveActionStatus;
  overdue: boolean;
  framework_tags: FrameworkControl[];
  closed_by: number | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CorrectiveActionCreateInput {
  title: string;
  nonconformity_description: string;
  root_cause?: string | null;
  action_description?: string | null;
  source_type?: string | null;
  source_id?: number | null;
  assignee_id: number;
  due_date: string;
}

export interface CorrectiveActionUpdateInput {
  title?: string;
  nonconformity_description?: string;
  root_cause?: string | null;
  action_description?: string | null;
  source_type?: string | null;
  source_id?: number | null;
  assignee_id?: number | null;
  due_date?: string;
  status?: "open" | "in_progress";
}
