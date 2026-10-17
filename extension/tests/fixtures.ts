import type { ScanRule } from "../../frontend/src/shared/dlp/detectors.ts";
import type { Policy, PolicyTool } from "../src/policy.ts";

export const CARD = "4111111111111111";

export const cardRule: ScanRule = {
  id: 1,
  name: "Payment card numbers",
  kind: "builtin",
  builtin_key: "credit_card",
  keywords: null,
  pattern: null,
  classification: "confidential",
  action: "block",
};

export const clientRule: ScanRule = {
  id: 2,
  name: "Client names",
  kind: "keywords",
  builtin_key: null,
  keywords: ["Project Falcon"],
  pattern: null,
  classification: "internal",
  action: "warn",
};

export const ticketRule: ScanRule = {
  id: 3,
  name: "Ticket numbers",
  kind: "regex",
  builtin_key: null,
  keywords: null,
  pattern: String.raw`\bPROJ-\d{4}\b`,
  classification: "internal",
  action: "monitor",
};

export function tool(overrides: Partial<PolicyTool> = {}): PolicyTool {
  return {
    name: "ChatGPT",
    domains: ["chatgpt.com", "chat.openai.com"],
    status: "catalogued",
    max_data_classification: "public",
    ...overrides,
  };
}

/** ChatGPT unapproved, Claude approved with limits (internal data), Copilot
 * approved for confidential data, and Grok whose access was withdrawn. */
export function makePolicy(overrides: Partial<Policy> = {}): Policy {
  return {
    unapproved_site_action: "warn",
    staff_notice: null,
    tools: [
      tool(),
      tool({
        name: "Claude",
        domains: ["claude.ai"],
        status: "restricted",
        max_data_classification: "internal",
      }),
      tool({
        name: "Microsoft Copilot",
        domains: ["copilot.microsoft.com"],
        status: "approved",
        max_data_classification: "confidential",
      }),
      tool({ name: "Grok", domains: ["grok.com"], status: "revoked" }),
    ],
    rules: [cardRule, clientRule, ticketRule],
    ...overrides,
  };
}
