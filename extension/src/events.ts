/**
 * The counts the extension reports. Metadata only, and aggregated here: one
 * number per day, site, kind of event, rule and action. Never a URL, a page
 * title, the time of day or any text.
 */

export type EventType = "unapproved_site" | "blocked_site" | "dlp_match" | "request_started";
export type UsageAction = "monitored" | "warned" | "blocked" | "overridden";

/** One day's count, in the shape the server's /agent/events takes. */
export interface UsageEvent {
  day: string;
  domain: string;
  event_type: EventType;
  rule_id: number | null;
  action: UsageAction;
  count: number;
}

/** The server accepts at most this many events in one request. */
export const MAX_BATCH = 500;
/** A single count the server will take. */
export const MAX_COUNT = 10_000;

function keyOf(event: Omit<UsageEvent, "count">): string {
  return JSON.stringify([event.day, event.domain, event.event_type, event.rule_id, event.action]);
}

/** The UTC day, which is how the server judges a day. */
export function utcDay(now: Date): string {
  return now.toISOString().slice(0, 10);
}

export class EventBuffer {
  private counts = new Map<string, UsageEvent>();

  /** Adds `n` to the count for this combination. */
  add(event: Omit<UsageEvent, "count">, n = 1): void {
    const key = keyOf(event);
    const existing = this.counts.get(key);
    if (existing) {
      existing.count = Math.min(MAX_COUNT, existing.count + n);
    } else {
      this.counts.set(key, { ...event, count: Math.min(MAX_COUNT, n) });
    }
  }

  /** How many separate counts are waiting. */
  get size(): number {
    return this.counts.size;
  }

  /** Removes and returns up to `max` counts, oldest first. */
  take(max: number = MAX_BATCH): UsageEvent[] {
    const batch: UsageEvent[] = [];
    for (const [key, event] of this.counts) {
      if (batch.length >= max) break;
      batch.push(event);
      this.counts.delete(key);
    }
    return batch;
  }

  /** Puts a batch back, adding to anything counted since. */
  restore(batch: UsageEvent[]): void {
    for (const { count, ...event } of batch) this.add(event, count);
  }

  toJSON(): UsageEvent[] {
    return [...this.counts.values()];
  }

  static fromJSON(value: unknown): EventBuffer {
    const buffer = new EventBuffer();
    if (!Array.isArray(value)) return buffer;
    for (const item of value as Partial<UsageEvent>[]) {
      if (
        typeof item?.day === "string" &&
        typeof item.domain === "string" &&
        typeof item.event_type === "string" &&
        typeof item.action === "string" &&
        typeof item.count === "number" &&
        item.count > 0
      ) {
        buffer.add(
          {
            day: item.day,
            domain: item.domain,
            event_type: item.event_type as EventType,
            rule_id: typeof item.rule_id === "number" ? item.rule_id : null,
            action: item.action as UsageAction,
          },
          item.count,
        );
      }
    }
    return buffer;
  }
}
