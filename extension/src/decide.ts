/**
 * What to do about a piece of text on an AI site: which rules it trips and
 * how strictly to treat it.
 */

import {
  type RuleAction,
  type RuleHit,
  scan,
  strictestAction,
} from "../../frontend/src/shared/dlp/detectors.ts";
import { type Policy, type ToolState, classify } from "./policy.ts";

export interface Decision {
  /** The strictest action among the rules that matched; null when none did. */
  action: RuleAction | null;
  hits: RuleHit[];
  state: ToolState;
  /** The catalogue domain the text is going to, for reporting. */
  domain: string;
  toolName: string;
}

/**
 * Checks `text` going to `host`. Null when the host isn't a catalogued AI
 * site -- the extension has nothing to say about it.
 *
 * A tool the organization has approved is held only to rules about data more
 * sensitive than it is cleared for; an unapproved one is treated as cleared
 * for public data only.
 */
export function decide(text: string, host: string, policy: Policy): Decision | null {
  const found = classify(host, policy);
  if (found === null) return null;
  const clearance = found.state === "unapproved" ? null : found.tool.max_data_classification;
  const hits = scan(text, policy.rules, clearance);
  return {
    action: strictestAction(hits),
    hits,
    state: found.state,
    domain: found.domain,
    toolName: found.tool.name,
  };
}
