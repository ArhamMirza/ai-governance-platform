import type { FrameworkControl } from "../framework-controls/types";

export type AuditScheduleType = "interval" | "ad_hoc";
export type AuditProgramStatus = "active" | "archived";
export type InternalAuditStatus = "planned" | "in_progress" | "completed";
export type AuditFindingType = "nonconformity" | "observation";

export interface AuditProgram {
  id: number;
  title: string;
  description: string | null;
  schedule_type: AuditScheduleType;
  interval_months: number | null;
  start_date: string | null;
  owner_id: number | null;
  status: AuditProgramStatus;
  next_due_date: string | null;
  overdue: boolean;
  framework_tags: FrameworkControl[];
  created_at: string;
  updated_at: string;
}

export interface AuditProgramCreateInput {
  title: string;
  description?: string | null;
  schedule_type: AuditScheduleType;
  interval_months?: number | null;
  start_date?: string | null;
  owner_id?: number | null;
}

export interface AuditProgramUpdateInput {
  title?: string;
  description?: string | null;
  schedule_type?: AuditScheduleType;
  interval_months?: number | null;
  start_date?: string | null;
  owner_id?: number | null;
  status?: AuditProgramStatus;
}

export interface InternalAudit {
  id: number;
  audit_program_id: number;
  title: string;
  planned_date: string;
  conducted_date: string | null;
  auditor_id: number | null;
  scope: string | null;
  conclusion: string | null;
  status: InternalAuditStatus;
  overdue: boolean;
  created_at: string;
  updated_at: string;
}

export interface InternalAuditCreateInput {
  title: string;
  planned_date: string;
  auditor_id?: number | null;
  scope?: string | null;
}

export interface InternalAuditUpdateInput {
  title?: string;
  planned_date?: string;
  auditor_id?: number | null;
  scope?: string | null;
  conclusion?: string | null;
  status?: "planned" | "in_progress";
}

export interface AuditFinding {
  id: number;
  internal_audit_id: number;
  description: string;
  finding_type: AuditFindingType;
  corrective_action_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface AuditFindingCreateInput {
  description: string;
  finding_type: AuditFindingType;
}

export interface AuditFindingUpdateInput {
  description?: string;
  finding_type?: AuditFindingType;
}
