/**
 * The extension's service worker: keeps the policy current, applies it to the
 * browser, and sends the counts.
 *
 * Manifest V3 service workers sleep and wake, so nothing is held only in
 * memory: the policy, the status and the waiting counts all live in
 * chrome.storage.local, and every entry point re-reads what it needs.
 */

import { reportingEmail } from "./config.ts";
import { DEV_CONFIG_KEY, loadConfig } from "./configSource.ts";
import { EventBuffer, type EventType, type UsageAction, utcDay } from "./events.ts";
import {
  EVENTS_KEY,
  type ExtensionMessage,
  POLICY_KEY,
  STATUS_KEY,
} from "./messages.ts";
import { type Policy, classify } from "./policy.ts";
import { ALLOW_RULE_ID_BASE, REDIRECT_RULE_ID_BASE, allowRule, contentScriptMatches, redirectRules } from "./rules.ts";
import { type StoredPolicy, type SyncStatus, flushEvents, syncPolicy } from "./sync.ts";

const BLOCKED_PAGE = "/blocked.html";
const CONTENT_SCRIPT_ID = "ai-governance-guard";
const POLICY_ALARM = "policy";
const FLUSH_ALARM = "flush";
const ALLOW_ALARM_PREFIX = "allow:";
/** How long "Continue" on a warning page lets a site through. */
const ALLOW_MINUTES = 60;
/** Send early once this many separate counts are waiting. */
const FLUSH_THRESHOLD = 50;

// ---------- storage ----------

async function readStored(): Promise<StoredPolicy> {
  const stored = (await chrome.storage.local.get(POLICY_KEY))[POLICY_KEY] as
    | Partial<StoredPolicy>
    | undefined;
  return { policy: stored?.policy ?? null, etag: stored?.etag ?? null };
}

async function writeStatus(status: SyncStatus, hasPolicy: boolean): Promise<void> {
  await chrome.storage.local.set({
    [STATUS_KEY]: { ...status, hasPolicy, at: new Date().toISOString() },
  });
  const healthy = hasPolicy && (status.kind === "ok" || status.kind === "unchanged");
  await chrome.action.setBadgeText({ text: healthy ? "" : "!" });
  await chrome.action.setBadgeBackgroundColor({ color: "#b91c1c" });
}

let bufferPromise: Promise<EventBuffer> | null = null;

function buffer(): Promise<EventBuffer> {
  bufferPromise ??= chrome.storage.local
    .get(EVENTS_KEY)
    .then((stored) => EventBuffer.fromJSON(stored[EVENTS_KEY]));
  return bufferPromise;
}

async function saveBuffer(): Promise<void> {
  await chrome.storage.local.set({ [EVENTS_KEY]: (await buffer()).toJSON() });
}

async function count(
  domain: string,
  eventType: EventType,
  action: UsageAction,
  ruleId: number | null = null,
): Promise<void> {
  (await buffer()).add({ day: utcDay(new Date()), domain, event_type: eventType, rule_id: ruleId, action });
  await saveBuffer();
  if ((await buffer()).size >= FLUSH_THRESHOLD) void flush();
}

// ---------- applying the policy ----------

async function applyPolicy(policy: Policy): Promise<void> {
  const existing = await chrome.declarativeNetRequest.getDynamicRules();
  const ours = existing
    .map((rule) => rule.id)
    .filter((id) => id >= REDIRECT_RULE_ID_BASE && id < ALLOW_RULE_ID_BASE);
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: ours,
    addRules: redirectRules(
      policy,
      policy.unapproved_site_action,
      BLOCKED_PAGE,
    ) as chrome.declarativeNetRequest.Rule[],
  });

  await chrome.scripting.unregisterContentScripts({ ids: [CONTENT_SCRIPT_ID] }).catch(() => {});
  const matches = contentScriptMatches(policy);
  if (matches.length > 0) {
    await chrome.scripting.registerContentScripts([
      {
        id: CONTENT_SCRIPT_ID,
        js: ["content.js"],
        matches,
        runAt: "document_start",
        allFrames: true,
        persistAcrossSessions: true,
      },
    ]);
  }
}

async function refreshPolicy(): Promise<void> {
  const config = await loadConfig();
  const stored = await readStored();
  if (config === null) {
    await writeStatus(
      { kind: "error", message: "Not configured: IT has not set the platform address and key." },
      stored.policy !== null,
    );
    return;
  }
  const result = await syncPolicy(config, stored);
  if (result.changed && result.policy !== null) {
    await chrome.storage.local.set({ [POLICY_KEY]: { policy: result.policy, etag: result.etag } });
    await applyPolicy(result.policy);
  }
  await writeStatus(result.status, result.policy !== null);
}

/** Re-applies the stored policy, for a worker or browser that has just started. */
async function reapply(): Promise<void> {
  const { policy } = await readStored();
  if (policy !== null) await applyPolicy(policy);
}

async function flush(): Promise<void> {
  const config = await loadConfig();
  if (config === null) return;
  const pending = await buffer();
  if (pending.size === 0) return;
  let email: string | undefined;
  try {
    email = (await chrome.identity.getProfileUserInfo({ accountStatus: "ANY" as never })).email;
  } catch {
    email = undefined;
  }
  await flushEvents(config, reportingEmail(email), pending);
  await saveBuffer();
}

// ---------- events from pages ----------

/** Allows a domain through a warning for a while. */
async function allowFor(domain: string): Promise<void> {
  const slot = Math.abs([...domain].reduce((sum, char) => (sum * 31 + char.charCodeAt(0)) | 0, 7)) % 900;
  const rule = allowRule(slot, domain);
  await chrome.declarativeNetRequest.updateSessionRules({
    removeRuleIds: [rule.id],
    addRules: [rule as chrome.declarativeNetRequest.Rule],
  });
  await chrome.alarms.create(`${ALLOW_ALARM_PREFIX}${rule.id}`, { delayInMinutes: ALLOW_MINUTES });
}

async function onMessage(message: ExtensionMessage, sender: chrome.runtime.MessageSender): Promise<void> {
  const { policy } = await readStored();
  if (policy === null) return;

  if (message.type === "dlp") {
    // The site is taken from where the message came from, not from what the
    // page says.
    const host = sender.url ? new URL(sender.url).hostname : "";
    const found = classify(host, policy);
    if (found !== null) await count(found.domain, "dlp_match", message.action, message.ruleId);
    return;
  }

  const found = classify(message.domain, policy);
  if (found === null) return;
  if (message.type === "interstitial") {
    if (message.mode === "block") await count(found.domain, "blocked_site", "blocked");
    else await count(found.domain, "unapproved_site", "warned");
  } else if (message.type === "continue") {
    await count(found.domain, "unapproved_site", "overridden");
    await allowFor(found.domain);
  } else if (message.type === "request") {
    await count(found.domain, "request_started", "monitored");
  }
}

chrome.runtime.onMessage.addListener((message: ExtensionMessage, sender, sendResponse) => {
  // Answer when done, so a page that is about to navigate can wait for the
  // allow rule it asked for.
  onMessage(message, sender).then(() => sendResponse(true), () => sendResponse(false));
  return true;
});

// In monitor mode nothing redirects, so visits to unapproved sites are counted here.
chrome.webNavigation.onCommitted.addListener(
  async (details) => {
    if (details.frameId !== 0) return;
    const { policy } = await readStored();
    if (policy === null || policy.unapproved_site_action !== "monitor") return;
    const found = classify(new URL(details.url).hostname, policy);
    if (found !== null && found.state === "unapproved") {
      await count(found.domain, "unapproved_site", "monitored");
    }
  },
  { url: [{ schemes: ["http", "https"] }] },
);

// ---------- lifecycle ----------

async function start(): Promise<void> {
  await chrome.alarms.create(POLICY_ALARM, { periodInMinutes: 15 });
  await chrome.alarms.create(FLUSH_ALARM, { periodInMinutes: 5 });
  await reapply();
  await refreshPolicy();
}

chrome.runtime.onInstalled.addListener(() => void start());
chrome.runtime.onStartup.addListener(() => void start());

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === POLICY_ALARM) void refreshPolicy();
  else if (alarm.name === FLUSH_ALARM) void flush();
  else if (alarm.name.startsWith(ALLOW_ALARM_PREFIX)) {
    const id = Number(alarm.name.slice(ALLOW_ALARM_PREFIX.length));
    void chrome.declarativeNetRequest.updateSessionRules({ removeRuleIds: [id] });
  }
});

// A change to what IT configured takes effect straight away.
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "managed" || (area === "local" && DEV_CONFIG_KEY in changes)) void refreshPolicy();
});
