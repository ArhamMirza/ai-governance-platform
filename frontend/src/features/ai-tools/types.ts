import type { FrameworkControl } from "../framework-controls/types";

/** `catalogued` is a known AI site nobody has approved -- where every tool starts. */
export type AIToolStatus = "catalogued" | "approved" | "restricted" | "revoked";
/** Only a `web` tool has addresses, and only those are watched by the browser
 * extension. The rest are governed by being on the register. */
export type AIToolKind = "web" | "desktop_app" | "local_model" | "editor_plugin" | "browser_extension";
export type DataClassification = "public" | "internal" | "confidential";
export type AIToolAction = "approve" | "restrict" | "revoke";
export type AIToolRequestStatus = "requested" | "approved" | "rejected";

export interface AIToolStanding {
  /** Approved, and past its review date. Computed by the server. */
  review_overdue: boolean;
}

export interface AITool {
  id: number;
  name: string;
  vendor: string | null;
  kind: AIToolKind;
  domains: string[];
  description: string | null;
  status: AIToolStatus;
  max_data_classification: DataClassification;
  conditions_of_use: string | null;
  owner_id: number | null;
  supplier_id: number | null;
  decided_by: number | null;
  decided_on: string | null;
  decision_note: string | null;
  review_due: string | null;
  standing: AIToolStanding;
  framework_tags: FrameworkControl[];
  created_at: string;
  updated_at: string;
}

export interface AIToolInput {
  name: string;
  vendor: string | null;
  kind: AIToolKind;
  domains: string[];
  description: string | null;
  owner_id: number | null;
  supplier_id: number | null;
}

export type AIToolUpdateInput = Partial<
  AIToolInput & {
    max_data_classification: DataClassification;
    conditions_of_use: string | null;
    review_due: string | null;
  }
>;

export interface AIToolDecisionInput {
  action: AIToolAction;
  max_data_classification: DataClassification | null;
  conditions_of_use: string | null;
  review_due: string | null;
  note: string | null;
}

/** A request as the governance team sees it. */
export interface AIToolRequest {
  id: number;
  requester_id: number;
  tool_id: number | null;
  tool_name: string;
  kind: AIToolKind;
  domain: string | null;
  purpose: string;
  data_involved: string | null;
  requested_on: string;
  status: AIToolRequestStatus;
  decided_by: number | null;
  decided_on: string | null;
  decision_note: string | null;
}

export interface AIToolRequestDecisionInput {
  action: "approve" | "reject";
  domain: string | null;
  max_data_classification: DataClassification | null;
  conditions_of_use: string | null;
  review_due: string | null;
  note: string | null;
}

/** What an employee may use, with the rules that go with it. */
export interface StaffAITool {
  id: number;
  name: string;
  vendor: string | null;
  kind: AIToolKind;
  domains: string[];
  status: "approved" | "restricted";
  max_data_classification: DataClassification;
  conditions_of_use: string | null;
}

/** A known tool that isn't allowed yet -- for the request form's picker. */
export interface StaffRequestableTool {
  id: number;
  name: string;
  vendor: string | null;
  kind: AIToolKind;
}

export interface StaffAIToolRequestInput {
  tool_id: number | null;
  tool_name: string;
  kind: AIToolKind;
  domain: string | null;
  purpose: string;
  data_involved: string | null;
}

/** An employee's own request and how it was answered. */
export interface StaffAIToolRequest {
  id: number;
  tool_name: string;
  kind: AIToolKind;
  domain: string | null;
  purpose: string;
  requested_on: string;
  status: AIToolRequestStatus;
  decided_on: string | null;
  decision_note: string | null;
}
