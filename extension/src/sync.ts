/**
 * Talking to the platform: fetching the policy and sending the counts.
 *
 * The rules about what to keep when something goes wrong are the point of this
 * file, so they are spelled out in the code and tested one by one:
 *   - the policy is only ever replaced by a valid newer one; an outage, a bad
 *     key or junk from a proxy leaves the last good policy in force
 *   - counts are kept until the platform has taken them, except a batch it
 *     refused outright -- retrying that would never succeed and would hold up
 *     everything behind it
 */

import type { Config } from "./config.ts";
import { type EventBuffer, MAX_BATCH, type UsageEvent } from "./events.ts";
import { type Policy, parsePolicy } from "./policy.ts";

export type SyncStatus =
  | { kind: "ok"; message: string }
  | { kind: "unchanged"; message: string }
  | { kind: "rejected"; message: string }
  | { kind: "offline"; message: string }
  | { kind: "error"; message: string };

export interface StoredPolicy {
  policy: Policy | null;
  etag: string | null;
}

export interface PolicyResult extends StoredPolicy {
  status: SyncStatus;
  /** Whether `policy` is different from what was stored, so it needs applying. */
  changed: boolean;
}

type Fetch = typeof fetch;

function headers(config: Config): Record<string, string> {
  return { Authorization: `Bearer ${config.enrollmentKey}` };
}

/**
 * Fetches the policy, sending the stored tag so an unchanged policy costs a
 * 304. Always returns something the caller can store: the new policy on
 * success, otherwise exactly what it had.
 */
export async function syncPolicy(
  config: Config,
  stored: StoredPolicy,
  doFetch: Fetch = fetch,
): Promise<PolicyResult> {
  const keep = (status: SyncStatus): PolicyResult => ({ ...stored, status, changed: false });
  const request: Record<string, string> = headers(config);
  if (stored.policy !== null && stored.etag !== null) request["If-None-Match"] = stored.etag;

  let response: Response;
  try {
    response = await doFetch(`${config.serverUrl}/api/v1/agent/policy`, { headers: request });
  } catch {
    return keep({ kind: "offline", message: "The platform could not be reached." });
  }

  if (response.status === 304) {
    return keep({ kind: "unchanged", message: "Policy is up to date." });
  }
  if (response.status === 401) {
    return keep({ kind: "rejected", message: "The platform did not accept the enrollment key." });
  }
  if (response.status === 429) {
    return keep({ kind: "rejected", message: "Too many wrong keys; the platform is refusing for now." });
  }
  if (!response.ok) {
    return keep({ kind: "error", message: `The platform answered ${response.status}.` });
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return keep({ kind: "error", message: "The platform's answer wasn't readable." });
  }
  const policy = parsePolicy(body);
  if (policy === null) {
    return keep({ kind: "error", message: "The platform's answer wasn't a policy." });
  }
  return {
    policy,
    etag: response.headers.get("etag"),
    status: { kind: "ok", message: "Policy updated." },
    changed: true,
  };
}

export interface FlushResult {
  /** How many counts the platform took. */
  sent: number;
  /** How many were thrown away because the platform refused them. */
  dropped: number;
  status: SyncStatus;
}

/**
 * Sends what has been counted, a batch at a time. A batch is put back in the
 * buffer unless the platform took it or refused it for good; the first
 * failure stops the run, so nothing is sent out of order or hammered.
 */
export async function flushEvents(
  config: Config,
  email: string,
  buffer: EventBuffer,
  doFetch: Fetch = fetch,
): Promise<FlushResult> {
  let sent = 0;
  let dropped = 0;
  while (buffer.size > 0) {
    const batch = buffer.take(MAX_BATCH);
    let response: Response;
    try {
      response = await doFetch(`${config.serverUrl}/api/v1/agent/events`, {
        method: "POST",
        headers: { ...headers(config), "Content-Type": "application/json" },
        body: JSON.stringify({ user_email: email, events: batch satisfies UsageEvent[] }),
      });
    } catch {
      buffer.restore(batch);
      return { sent, dropped, status: { kind: "offline", message: "The platform could not be reached." } };
    }

    if (response.ok) {
      sent += batch.length;
    } else if (response.status === 400 || response.status === 404 || response.status === 422) {
      // The platform understood and refused: retrying would never work.
      dropped += batch.length;
    } else {
      buffer.restore(batch);
      const kind = response.status === 401 || response.status === 429 ? "rejected" : "error";
      return {
        sent,
        dropped,
        status: { kind, message: `The platform answered ${response.status}.` },
      };
    }
  }
  return { sent, dropped, status: { kind: "ok", message: "Counts sent." } };
}

/**
 * Tells the platform this browser has the extension: who, and which version,
 * and nothing else. It is how the platform knows who is covered, including
 * people who haven't visited an AI site and so have no counts. Returns whether
 * the platform took it, so the caller can try again later if not.
 */
export async function sendCheckin(
  config: Config,
  email: string,
  version: string,
  doFetch: Fetch = fetch,
): Promise<boolean> {
  try {
    const response = await doFetch(`${config.serverUrl}/api/v1/agent/checkin`, {
      method: "POST",
      headers: { ...headers(config), "Content-Type": "application/json" },
      body: JSON.stringify({ user_email: email, version }),
    });
    return response.ok;
  } catch {
    return false;
  }
}
