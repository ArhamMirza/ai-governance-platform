import type { FrameworkControl } from "../framework-controls/types";

export type IncidentSeverity = "low" | "medium" | "high" | "critical";
export type IncidentStatus = "open" | "investigating" | "resolved";
/** EU AI Act Art. 73 -- each sets how long there is to notify the authority. */
export type SeriousIncidentCategory = "widespread_or_critical_infrastructure" | "death" | "other";

export interface Incident {
  id: number;
  title: string;
  description: string;
  ai_system_row_id: number | null;
  detected_on: string;
  occurred_on: string | null;
  severity: IncidentSeverity;
  status: IncidentStatus;
  owner_id: number | null;
  impact_description: string | null;
  immediate_actions: string | null;
  root_cause: string | null;
  is_serious: boolean;
  serious_category: SeriousIncidentCategory | null;
  authority_notified_on: string | null;
  authority_reference: string | null;
  reporting_deadline: string | null;
  reporting_overdue: boolean;
  corrective_action_ids: number[];
  framework_tags: FrameworkControl[];
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentCreateInput {
  title: string;
  description: string;
  ai_system_row_id?: number | null;
  detected_on: string;
  occurred_on?: string | null;
  severity?: IncidentSeverity;
  owner_id?: number | null;
  is_serious?: boolean;
  serious_category?: SeriousIncidentCategory | null;
}

export interface IncidentUpdateInput {
  title?: string;
  description?: string;
  ai_system_row_id?: number | null;
  detected_on?: string;
  occurred_on?: string | null;
  severity?: IncidentSeverity;
  status?: IncidentStatus;
  owner_id?: number | null;
  impact_description?: string | null;
  immediate_actions?: string | null;
  root_cause?: string | null;
  is_serious?: boolean;
  serious_category?: SeriousIncidentCategory | null;
  authority_notified_on?: string | null;
  authority_reference?: string | null;
}
