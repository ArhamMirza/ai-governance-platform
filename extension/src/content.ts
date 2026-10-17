/**
 * Runs on the AI sites the platform has catalogued, and only those: the
 * background registers this script for exactly the catalogued domains.
 *
 * It keeps the current policy from storage and hands the page's events to the
 * guard (guard.ts). Nothing is sent anywhere from here except a rule's number
 * and what happened to it.
 */

import { showDialog } from "./dialog.ts";
import { installGuards } from "./guard.ts";
import { POLICY_KEY, type DlpMessage } from "./messages.ts";
import type { Policy } from "./policy.ts";

let policy: Policy | null = null;

function fromStored(value: unknown): Policy | null {
  const stored = value as { policy?: Policy | null } | undefined;
  return stored?.policy ?? null;
}

void chrome.storage.local.get(POLICY_KEY).then((stored) => {
  policy = fromStored(stored[POLICY_KEY]);
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && POLICY_KEY in changes) {
    policy = fromStored(changes[POLICY_KEY].newValue);
  }
});

/** A dropped file set can't be re-sent as it was; rebuild it and drop it again. */
function replayDrop(target: EventTarget, files: File[]): void {
  const transfer = new DataTransfer();
  for (const file of files) transfer.items.add(file);
  target.dispatchEvent(
    new DragEvent("drop", { dataTransfer: transfer, bubbles: true, cancelable: true }),
  );
}

installGuards(document, {
  host: location.hostname,
  getPolicy: () => policy,
  report: (match) => {
    const message: DlpMessage = { type: "dlp", ruleId: match.ruleId, action: match.action };
    // The background may be asleep or the extension reloading; a lost count is
    // better than an error in someone else's page.
    chrome.runtime.sendMessage(message).catch(() => {});
  },
  confirm: (request) => showDialog(document, request),
  replayDrop,
});
