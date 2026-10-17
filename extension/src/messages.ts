/**
 * The few messages the parts of the extension send each other. Deliberately
 * small, and none carries text, a URL or a title: the content script says
 * which rule matched and what happened, and the background works out the site
 * from the sender itself rather than trusting the page.
 */

import type { UsageAction } from "./events.ts";

/** A rule matched on an AI site. */
export interface DlpMessage {
  type: "dlp";
  ruleId: number;
  action: UsageAction;
}

/** The blocked page was shown. */
export interface InterstitialMessage {
  type: "interstitial";
  domain: string;
  mode: "warn" | "block";
}

/** The person chose to carry on from a warning page. */
export interface ContinueMessage {
  type: "continue";
  domain: string;
}

/** The person went to request the tool. */
export interface RequestMessage {
  type: "request";
  domain: string;
}

export type ExtensionMessage = DlpMessage | InterstitialMessage | ContinueMessage | RequestMessage;

export const POLICY_KEY = "policy";
export const STATUS_KEY = "status";
export const EVENTS_KEY = "events";
