import type { AITool, AIToolRequest, StaffAITool } from "../types";

export function makeTool(overrides: Partial<AITool> = {}): AITool {
  return {
    id: 1,
    name: "Claude",
    vendor: "Anthropic",
    kind: "web",
    domains: ["claude.ai"],
    description: null,
    status: "catalogued",
    max_data_classification: "public",
    conditions_of_use: null,
    owner_id: null,
    supplier_id: null,
    decided_by: null,
    decided_on: null,
    decision_note: null,
    review_due: null,
    standing: { review_overdue: false },
    framework_tags: [],
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    ...overrides,
  };
}

export function makeRequest(overrides: Partial<AIToolRequest> = {}): AIToolRequest {
  return {
    id: 1,
    requester_id: 3,
    tool_id: null,
    tool_name: "Perplexity",
    kind: "web",
    domain: "perplexity.ai",
    purpose: "Checking public sources while researching suppliers.",
    data_involved: null,
    requested_on: "2026-06-01",
    status: "requested",
    decided_by: null,
    decided_on: null,
    decision_note: null,
    ...overrides,
  };
}

export function makeStaffTool(overrides: Partial<StaffAITool> = {}): StaffAITool {
  return {
    id: 1,
    name: "Microsoft Copilot",
    vendor: "Microsoft",
    kind: "web",
    domains: ["copilot.microsoft.com"],
    status: "approved",
    max_data_classification: "internal",
    conditions_of_use: null,
    ...overrides,
  };
}
