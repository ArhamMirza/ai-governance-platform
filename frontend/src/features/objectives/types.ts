import type { FrameworkControl } from "../framework-controls/types";

export type ObjectiveKind = "measured" | "milestone";
export type TargetDirection = "at_least" | "at_most";
export type ObjectiveStatus = "active" | "achieved" | "not_achieved" | "withdrawn";
/** Computed by the server from the objective and its readings, never stored. */
export type ObjectiveState =
  | "not_measured"
  | "on_track"
  | "off_track"
  | "missed"
  | "in_progress"
  | "achieved"
  | "not_achieved"
  | "withdrawn";

export interface ObjectiveStanding {
  state: ObjectiveState;
  latest_value: number | null;
  latest_on: string | null;
  next_measurement_due: string | null;
  measurement_overdue: boolean;
}

export interface Measurement {
  id: number;
  objective_id: number;
  measured_on: string;
  value: number;
  note: string | null;
  recorded_by: number | null;
  created_at: string;
}

export interface Objective {
  id: number;
  title: string;
  description: string | null;
  kind: ObjectiveKind;
  owner_id: number | null;
  policy_id: number | null;
  established_on: string;
  target_date: string | null;
  planned_actions: string | null;
  resources: string | null;
  evaluation_method: string | null;
  metric_name: string | null;
  unit: string | null;
  direction: TargetDirection | null;
  target_value: number | null;
  baseline_value: number | null;
  measurement_interval_months: number | null;
  first_measurement_due: string | null;
  status: ObjectiveStatus;
  closed_on: string | null;
  closure_note: string | null;
  ai_system_row_ids: number[];
  standing: ObjectiveStanding;
  framework_tags: FrameworkControl[];
  created_at: string;
  updated_at: string;
}

export interface ObjectiveDetail extends Objective {
  /** Newest first. */
  measurements: Measurement[];
}

/** One objective as it stood on a past date -- for a management review. */
export interface ObjectiveAsOf {
  id: number;
  title: string;
  kind: ObjectiveKind;
  metric_name: string | null;
  unit: string | null;
  direction: TargetDirection | null;
  target_value: number | null;
  target_date: string | null;
  owner_id: number | null;
  standing: ObjectiveStanding;
}

export interface ObjectiveInput {
  title: string;
  description: string | null;
  kind: ObjectiveKind;
  owner_id: number | null;
  policy_id: number | null;
  established_on: string | null;
  target_date: string | null;
  planned_actions: string | null;
  resources: string | null;
  evaluation_method: string | null;
  metric_name: string | null;
  unit: string | null;
  direction: TargetDirection | null;
  target_value: number | null;
  baseline_value: number | null;
  measurement_interval_months: number | null;
  first_measurement_due: string | null;
}

export type ObjectiveUpdateInput = Partial<ObjectiveInput>;

export interface MeasurementInput {
  measured_on: string;
  value: number;
  note: string | null;
}

export interface ObjectiveCloseInput {
  status: Exclude<ObjectiveStatus, "active">;
  closure_note: string | null;
}
