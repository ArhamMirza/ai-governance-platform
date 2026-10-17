/**
 * Turning the policy into what the browser enforces: redirect rules for the
 * sites nobody has approved, and the list of pages the checking script runs on.
 */

import type { RuleAction } from "../../frontend/src/shared/dlp/detectors.ts";
import { type Policy, unapprovedDomains, watchedDomains } from "./policy.ts";

/** Dynamic rule ids we own, so replacing them never touches anyone else's. */
export const REDIRECT_RULE_ID_BASE = 1000;
/** Session rules that let a person through a warning for a while. */
export const ALLOW_RULE_ID_BASE = 5000;

export interface RedirectRule {
  id: number;
  priority: number;
  action: { type: "redirect"; redirect: { extensionPath: string } };
  condition: { requestDomains: string[]; resourceTypes: ["main_frame"] };
}

export interface AllowRule {
  id: number;
  priority: number;
  action: { type: "allow" };
  condition: { requestDomains: string[]; resourceTypes: ["main_frame"] };
}

/**
 * The extension page an unapproved site is sent to, as a path inside the
 * extension. The tool's name and the mode ride in the query so the page can
 * say what happened; no account or page detail does.
 */
export function blockedPagePath(
  blockedPage: string,
  domain: string,
  toolName: string,
  mode: "warn" | "block",
): string {
  const query = new URLSearchParams({ domain, tool: toolName, mode });
  return `${blockedPage}?${query.toString()}`;
}

/** Redirect rules for every unapproved tool, when the setting is to warn or
 * block. Monitor mode redirects nothing: it only counts. */
export function redirectRules(
  policy: Policy,
  action: RuleAction,
  blockedPage: string,
): RedirectRule[] {
  if (action === "monitor") return [];
  return unapprovedDomains(policy).map(({ domain, tool }, index) => ({
    id: REDIRECT_RULE_ID_BASE + index,
    priority: 1,
    action: {
      type: "redirect",
      redirect: { extensionPath: blockedPagePath(blockedPage, domain, tool.name, action) },
    },
    condition: { requestDomains: [domain], resourceTypes: ["main_frame"] },
  }));
}

/** Lets one domain through for now. Higher priority than the redirect, so it wins. */
export function allowRule(slot: number, domain: string): AllowRule {
  return {
    id: ALLOW_RULE_ID_BASE + slot,
    priority: 2,
    action: { type: "allow" },
    condition: { requestDomains: [domain], resourceTypes: ["main_frame"] },
  };
}

/** Match patterns for the checking script: the catalogued domains and their
 * subdomains, and nothing else, so it never loads on any other page. */
export function contentScriptMatches(policy: Policy): string[] {
  return watchedDomains(policy).flatMap((domain) => [`*://${domain}/*`, `*://*.${domain}/*`]);
}
