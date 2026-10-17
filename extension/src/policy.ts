/**
 * The policy the platform hands the extension (GET /api/v1/agent/policy), and
 * the question the whole extension turns on: is this address one of the AI
 * tools the organization knows about, and is it allowed?
 *
 * Pure functions with no browser API, so they are tested directly.
 */

import type { Classification, RuleAction, ScanRule } from "../../frontend/src/shared/dlp/detectors.ts";

export type ToolStatus = "catalogued" | "approved" | "restricted" | "revoked";

/** `unapproved` covers a tool nobody has approved and one whose access was withdrawn. */
export type ToolState = "approved" | "restricted" | "unapproved";

export interface PolicyTool {
  name: string;
  domains: string[];
  status: ToolStatus;
  max_data_classification: Classification;
}

export interface Policy {
  unapproved_site_action: RuleAction;
  staff_notice: string | null;
  tools: PolicyTool[];
  rules: ScanRule[];
}

export interface Classified {
  tool: PolicyTool;
  state: ToolState;
  /** The catalogue's own domain the host belongs to, which is what is reported. */
  domain: string;
}

const ACTIONS: readonly string[] = ["monitor", "warn", "block"];
const STATUSES: readonly string[] = ["catalogued", "approved", "restricted", "revoked"];

/** Whether `host` is `domain` or a subdomain of it, label for label:
 * `chatgpt.com.evil.net` and `notchatgpt.com` are not `chatgpt.com`. */
export function hostMatches(host: string, domain: string): boolean {
  const h = host.toLowerCase().replace(/\.$/, "");
  return h === domain || h.endsWith("." + domain);
}

function stateOf(status: ToolStatus): ToolState {
  if (status === "approved") return "approved";
  if (status === "restricted") return "restricted";
  return "unapproved";
}

/**
 * The catalogued tool a host belongs to, or null when it isn't an AI site the
 * organization knows. The most specific domain wins, so a tool at
 * `gemini.google.com` is not swallowed by one at `google.com`.
 */
export function classify(host: string, policy: Policy): Classified | null {
  let best: Classified | null = null;
  for (const tool of policy.tools) {
    for (const domain of tool.domains) {
      if (hostMatches(host, domain) && (best === null || domain.length > best.domain.length)) {
        best = { tool, state: stateOf(tool.status), domain };
      }
    }
  }
  return best;
}

/** Every domain the extension watches, once each. */
export function watchedDomains(policy: Policy): string[] {
  return [...new Set(policy.tools.flatMap((tool) => tool.domains))];
}

/** The tools nobody has approved, which is where the site control acts. */
export function unapprovedDomains(policy: Policy): { domain: string; tool: PolicyTool }[] {
  return policy.tools
    .filter((tool) => stateOf(tool.status) === "unapproved")
    .flatMap((tool) => tool.domains.map((domain) => ({ domain, tool })));
}

/**
 * The policy if `value` has the shape the extension depends on, else null. A
 * server answering with something else (a proxy's error page, a newer API)
 * must leave the last good policy in place rather than replace it with junk.
 */
export function parsePolicy(value: unknown): Policy | null {
  if (typeof value !== "object" || value === null) return null;
  const candidate = value as Record<string, unknown>;
  if (!ACTIONS.includes(String(candidate.unapproved_site_action))) return null;
  if (!Array.isArray(candidate.tools) || !Array.isArray(candidate.rules)) return null;
  for (const tool of candidate.tools as Record<string, unknown>[]) {
    if (
      typeof tool?.name !== "string" ||
      !Array.isArray(tool.domains) ||
      !tool.domains.every((domain) => typeof domain === "string") ||
      !STATUSES.includes(String(tool.status))
    ) {
      return null;
    }
  }
  for (const rule of candidate.rules as Record<string, unknown>[]) {
    if (typeof rule?.id !== "number" || typeof rule.name !== "string") return null;
    if (!ACTIONS.includes(String(rule.action))) return null;
  }
  return candidate as unknown as Policy;
}
