import type { FrameworkControl } from "../framework-controls/types";

export type ImprovementSource =
  | "internal_audit"
  | "management_review"
  | "concern"
  | "incident"
  | "corrective_action"
  | "objective"
  | "stakeholder_feedback"
  | "idea"
  | "other";

/** The records an improvement can point back to. */
export type ImprovementSourceType =
  | "AuditFinding"
  | "ManagementReviewMeeting"
  | "Concern"
  | "AIIncident"
  | "CorrectiveAction"
  | "AIObjective";

export type ImprovementStatus = "proposed" | "accepted" | "implemented" | "declined";
export type ImprovementAction = "accept" | "implement" | "decline" | "reopen";

/** Computed by the server from the improvement's dates, never stored. */
export interface ImprovementStanding {
  state: ImprovementStatus;
  /** Still open and past its target date. */
  overdue: boolean;
}

export interface Improvement {
  id: number;
  title: string;
  description: string | null;
  expected_benefit: string | null;
  source: ImprovementSource;
  source_type: ImprovementSourceType | null;
  source_id: number | null;
  /** What the source record is called, or null once it no longer exists. */
  source_label: string | null;
  owner_id: number | null;
  raised_on: string;
  target_date: string;
  status: ImprovementStatus;
  decided_on: string | null;
  closed_on: string | null;
  outcome: string | null;
  decline_reason: string | null;
  change_id: number | null;
  standing: ImprovementStanding;
  framework_tags: FrameworkControl[];
  created_at: string;
  updated_at: string;
}

/** One improvement as it stood on a past date -- for a management review. */
export interface ImprovementAsOf {
  id: number;
  title: string;
  source: ImprovementSource;
  owner_id: number | null;
  target_date: string;
  standing: ImprovementStanding;
}

export interface ImprovementInput {
  title: string;
  description: string | null;
  expected_benefit: string | null;
  source: ImprovementSource;
  source_type: ImprovementSourceType | null;
  source_id: number | null;
  owner_id: number | null;
  raised_on: string | null;
  target_date: string;
}

export type ImprovementUpdateInput = Partial<
  Pick<
    ImprovementInput,
    "title" | "description" | "expected_benefit" | "owner_id" | "raised_on" | "target_date"
  >
>;

export interface ImprovementStatusInput {
  action: ImprovementAction;
  note: string | null;
}
