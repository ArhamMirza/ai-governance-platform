import type { FrameworkControl } from "../framework-controls/types";

export interface ManagementReviewSettings {
  interval_months: number | null;
  start_date: string | null;
  next_due_date: string | null;
  overdue: boolean;
  framework_tags: FrameworkControl[];
  updated_at: string | null;
}

export interface ManagementReviewSettingsUpdateInput {
  interval_months: number | null;
  start_date?: string | null;
}

export interface ManagementReviewMeeting {
  id: number;
  meeting_date: string;
  chaired_by: number | null;
  attendees: string | null;
  previous_actions_status: string | null;
  context_changes: string | null;
  performance_summary: string | null;
  stakeholder_feedback: string | null;
  resource_adequacy: string | null;
  improvement_opportunities: string | null;
  decisions_and_actions: string | null;
  framework_tags: FrameworkControl[];
  created_at: string;
  updated_at: string;
}

export interface ManagementReviewMeetingCreateInput {
  meeting_date: string;
  chaired_by?: number | null;
  attendees?: string | null;
  previous_actions_status?: string | null;
  context_changes?: string | null;
  performance_summary?: string | null;
  stakeholder_feedback?: string | null;
  resource_adequacy?: string | null;
  improvement_opportunities?: string | null;
  decisions_and_actions?: string | null;
}

export interface ManagementReviewMeetingUpdateInput {
  meeting_date?: string;
  chaired_by?: number | null;
  attendees?: string | null;
  previous_actions_status?: string | null;
  context_changes?: string | null;
  performance_summary?: string | null;
  stakeholder_feedback?: string | null;
  resource_adequacy?: string | null;
  improvement_opportunities?: string | null;
  decisions_and_actions?: string | null;
}
