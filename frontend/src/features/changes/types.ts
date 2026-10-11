import type { FrameworkControl } from "../framework-controls/types";

export type ChangeType = "ai_system" | "process" | "policy" | "organization" | "other";
export type ChangeStatus = "planned" | "in_progress" | "implemented" | "cancelled";
export type ChangeAction = "start" | "implement" | "cancel" | "reopen";

/** Computed by the server from the change's dates, never stored. */
export interface ChangeStanding {
  state: ChangeStatus;
  /** Still open and past its planned date. */
  overdue: boolean;
}

export interface Change {
  id: number;
  title: string;
  description: string | null;
  change_type: ChangeType;
  reason: string | null;
  consequences: string | null;
  resources_needed: string | null;
  owner_id: number | null;
  raised_on: string;
  planned_date: string;
  status: ChangeStatus;
  started_on: string | null;
  closed_on: string | null;
  closure_note: string | null;
  ai_system_row_ids: number[];
  standing: ChangeStanding;
  framework_tags: FrameworkControl[];
  created_at: string;
  updated_at: string;
}

/** One change as it stood on a past date -- for a management review. */
export interface ChangeAsOf {
  id: number;
  title: string;
  change_type: ChangeType;
  owner_id: number | null;
  planned_date: string;
  standing: ChangeStanding;
}

export interface ChangeInput {
  title: string;
  description: string | null;
  change_type: ChangeType;
  reason: string | null;
  consequences: string | null;
  resources_needed: string | null;
  owner_id: number | null;
  raised_on: string | null;
  planned_date: string;
}

export type ChangeUpdateInput = Partial<ChangeInput>;

export interface ChangeStatusInput {
  action: ChangeAction;
  note: string | null;
}
