import type { FrameworkControl } from "../framework-controls/types";

export type ConcernCategory =
  | "safety_or_harm"
  | "bias_or_fairness"
  | "privacy_or_data"
  | "misuse_or_breach"
  | "transparency"
  | "accuracy_or_reliability"
  | "other";
export type ConcernChannel = "employee_portal" | "phone" | "email" | "in_person" | "other";
export type ConcernStatus = "received" | "under_review" | "resolved" | "not_actioned";
export type ConcernOutcome =
  | "substantiated"
  | "partly_substantiated"
  | "not_substantiated"
  | "no_finding";
export type ConcernAction = "acknowledge" | "resolve" | "dismiss" | "reopen";

// ---------- what an employee sends and sees ----------

export interface ConcernSubmitInput {
  category: ConcernCategory;
  description: string;
  ai_system_row_id: number | null;
  system_note: string | null;
  anonymous: boolean;
}

/** A concern as its own reporter sees it -- never internal notes or who is
 * handling it. */
export interface ReporterConcern {
  id: number;
  category: ConcernCategory;
  description: string;
  received_on: string;
  status: ConcernStatus;
  acknowledged_on: string | null;
  closed_on: string | null;
  outcome: ConcernOutcome | null;
  reply_to_reporter: string | null;
  is_anonymous: boolean;
}

/** Returned once; only a hash of the code is kept, so it can't be shown again. */
export interface ConcernSubmitted {
  tracking_code: string;
  concern: ReporterConcern;
}

export interface StaffAISystem {
  id: number;
  name: string;
}

export interface ConcernsProcess {
  process_description: string | null;
  acknowledge_within_days: number;
}

// ---------- what a handler sends and sees ----------

export interface Concern {
  id: number;
  category: ConcernCategory;
  description: string;
  ai_system_row_id: number | null;
  system_note: string | null;
  channel: ConcernChannel;
  received_on: string;
  is_anonymous: boolean;
  reporter_id: number | null;
  /** Null for an anonymous concern -- nothing identifying is stored. */
  reporter_name: string | null;
  reporter_note: string | null;
  status: ConcernStatus;
  handler_id: number | null;
  acknowledged_on: string | null;
  closed_on: string | null;
  outcome: ConcernOutcome | null;
  internal_notes: string | null;
  closure_note: string | null;
  reply_to_reporter: string | null;
  incident_id: number | null;
  /** Computed by the server, never stored. */
  acknowledge_by: string;
  awaiting_triage: boolean;
}

export interface ConcernLogInput {
  category: ConcernCategory;
  description: string;
  channel: Exclude<ConcernChannel, "employee_portal">;
  received_on: string | null;
  ai_system_row_id: number | null;
  system_note: string | null;
  anonymous: boolean;
  reporter_note: string | null;
}

export interface ConcernUpdateInput {
  category?: ConcernCategory;
  ai_system_row_id?: number | null;
  system_note?: string | null;
  handler_id?: number | null;
  internal_notes?: string | null;
  reply_to_reporter?: string | null;
}

export interface ConcernStatusInput {
  action: ConcernAction;
  outcome: ConcernOutcome | null;
  note: string | null;
}

export interface RaiseCorrectiveActionInput {
  title: string;
  action_description: string | null;
  assignee_id: number;
  due_date: string;
}

export interface ConcernSettings {
  id: number;
  process_description: string | null;
  acknowledge_within_days: number;
  framework_tags: FrameworkControl[];
}

export interface ConcernSettingsInput {
  process_description?: string | null;
  acknowledge_within_days?: number;
}
