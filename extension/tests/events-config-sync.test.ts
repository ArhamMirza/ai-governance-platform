import { describe, expect, it, vi } from "vitest";

import { UNIDENTIFIED_USER, parseConfig, reportingEmail, requestUrl } from "../src/config.ts";
import { EventBuffer, MAX_BATCH, MAX_COUNT, type UsageEvent, utcDay } from "../src/events.ts";
import { flushEvents, sendCheckin, syncPolicy } from "../src/sync.ts";
import { makePolicy } from "./fixtures.ts";

const config = { serverUrl: "https://gov.example.com", portalUrl: "https://portal.example.com", enrollmentKey: "aigk_key" };

function event(overrides: Partial<Omit<UsageEvent, "count">> = {}): Omit<UsageEvent, "count"> {
  return {
    day: "2026-06-01",
    domain: "chatgpt.com",
    event_type: "unapproved_site",
    rule_id: null,
    action: "warned",
    ...overrides,
  };
}

describe("EventBuffer", () => {
  it("adds up the same event and keeps different ones apart", () => {
    const buffer = new EventBuffer();

    buffer.add(event());
    buffer.add(event(), 4);
    buffer.add(event({ action: "overridden" }));
    buffer.add(event({ domain: "claude.ai" }));
    buffer.add(event({ day: "2026-06-02" }));
    buffer.add(event({ event_type: "dlp_match", rule_id: 1 }));
    buffer.add(event({ event_type: "dlp_match", rule_id: 2 }));

    expect(buffer.size).toBe(6);
    expect(buffer.toJSON().find((e) => e.action === "warned" && e.rule_id === null && e.domain === "chatgpt.com" && e.day === "2026-06-01")?.count).toBe(5);
  });

  it("never holds a count the server would refuse", () => {
    const buffer = new EventBuffer();

    buffer.add(event({ domain: "first.ai" }), MAX_COUNT + 5);
    buffer.add(event({ domain: "second.ai" }), MAX_COUNT);
    buffer.add(event({ domain: "second.ai" }), 50);

    expect(buffer.toJSON().map((e) => e.count)).toEqual([MAX_COUNT, MAX_COUNT]);
  });

  it("hands over a batch and forgets it, oldest first", () => {
    const buffer = new EventBuffer();
    for (const domain of ["a.ai", "b.ai", "c.ai"]) buffer.add(event({ domain }));

    const batch = buffer.take(2);

    expect(batch.map((e) => e.domain)).toEqual(["a.ai", "b.ai"]);
    expect(buffer.size).toBe(1);
    expect(buffer.take().map((e) => e.domain)).toEqual(["c.ai"]);
    expect(buffer.take()).toEqual([]);
  });

  it("takes at most a request's worth by default", () => {
    const buffer = new EventBuffer();
    for (let i = 0; i < MAX_BATCH + 25; i += 1) buffer.add(event({ domain: `site${i}.ai` }));

    expect(buffer.take()).toHaveLength(MAX_BATCH);
    expect(buffer.size).toBe(25);
  });

  it("puts a batch back, adding to anything counted since", () => {
    const buffer = new EventBuffer();
    buffer.add(event(), 3);
    const batch = buffer.take();
    buffer.add(event(), 2);

    buffer.restore(batch);

    expect(buffer.toJSON()).toEqual([{ ...event(), count: 5 }]);
  });

  it("survives being stored and read back", () => {
    const buffer = new EventBuffer();
    buffer.add(event({ event_type: "dlp_match", rule_id: 9, action: "blocked" }), 2);
    buffer.add(event());

    const restored = EventBuffer.fromJSON(JSON.parse(JSON.stringify(buffer.toJSON())));

    expect(restored.toJSON()).toEqual(buffer.toJSON());
  });

  it("ignores whatever in storage isn't a count", () => {
    const restored = EventBuffer.fromJSON([
      null,
      "x",
      { day: "2026-06-01" },
      { ...event(), count: 0 },
      { ...event(), count: -3 },
      { ...event(), count: 2 },
    ]);

    expect(restored.toJSON()).toEqual([{ ...event(), count: 2 }]);
    expect(EventBuffer.fromJSON(undefined).size).toBe(0);
    expect(EventBuffer.fromJSON("junk").size).toBe(0);
  });

  it("names the day in UTC, which is how the server judges it", () => {
    expect(utcDay(new Date("2026-06-01T23:59:59-05:00"))).toBe("2026-06-02");
    expect(utcDay(new Date("2026-06-01T00:00:00Z"))).toBe("2026-06-01");
    // Late evening UTC is already the next day in some places, but not for the server.
    expect(utcDay(new Date("2026-06-01T22:30:00Z"))).toBe("2026-06-01");
    expect(utcDay(new Date("2026-06-02T01:30:00+05:00"))).toBe("2026-06-01");
  });
});

describe("parseConfig", () => {
  it("accepts a secure address and a key", () => {
    expect(parseConfig({ serverUrl: " https://gov.example.com/ ", enrollmentKey: " aigk_x " })).toEqual({
      serverUrl: "https://gov.example.com",
      portalUrl: "https://gov.example.com",
      enrollmentKey: "aigk_x",
    });
  });

  it("uses a separate portal address when given", () => {
    expect(
      parseConfig({ serverUrl: "https://api.example.com", portalUrl: "https://app.example.com/", enrollmentKey: "k" })
        ?.portalUrl,
    ).toBe("https://app.example.com");
  });

  it("falls back to the server for a portal address that isn't usable", () => {
    expect(
      parseConfig({ serverUrl: "https://api.example.com", portalUrl: "http://app.example.com", enrollmentKey: "k" })
        ?.portalUrl,
    ).toBe("https://api.example.com");
  });

  it("allows plain http for the developer's own machine only", () => {
    expect(parseConfig({ serverUrl: "http://localhost:8000", enrollmentKey: "k" })?.serverUrl).toBe("http://localhost:8000");
    expect(parseConfig({ serverUrl: "http://127.0.0.1:8000", enrollmentKey: "k" })).not.toBeNull();
    expect(parseConfig({ serverUrl: "http://gov.example.com", enrollmentKey: "k" })).toBeNull();
    expect(parseConfig({ serverUrl: "http://localhost.evil.com", enrollmentKey: "k" })).toBeNull();
  });

  it.each([
    ["no settings", undefined],
    ["null settings", null],
    ["nothing set", {}],
    ["no key", { serverUrl: "https://gov.example.com" }],
    ["a blank key", { serverUrl: "https://gov.example.com", enrollmentKey: "  " }],
    ["no address", { enrollmentKey: "k" }],
    ["a nonsense address", { serverUrl: "not a url", enrollmentKey: "k" }],
    ["an unusable scheme", { serverUrl: "ftp://gov.example.com", enrollmentKey: "k" }],
    ["a key that isn't text", { serverUrl: "https://gov.example.com", enrollmentKey: 5 }],
  ])("is null for %s", (_name, managed) => {
    expect(parseConfig(managed as Record<string, unknown> | undefined)).toBeNull();
  });
});

describe("reportingEmail and requestUrl", () => {
  it("files an unidentified profile under a placeholder so its counts still arrive", () => {
    expect(reportingEmail("  Elena@Example.COM ")).toBe("elena@example.com");
    for (const none of [undefined, null, "", "  ", "not-an-email", "a@b"]) {
      expect(reportingEmail(none)).toBe(UNIDENTIFIED_USER);
    }
  });

  it("sends a person to the portal's request page with the tool filled in", () => {
    const url = new URL(requestUrl(config, "Chat & Co", "chat.example.ai"));

    expect(url.origin + url.pathname).toBe("https://portal.example.com/tools");
    expect(url.searchParams.get("name")).toBe("Chat & Co");
    expect(url.searchParams.get("domain")).toBe("chat.example.ai");
  });
});

// ---------- talking to the platform ----------

function reply(status: number, body?: unknown, headers: Record<string, string> = {}): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status, headers });
}

const stored = { policy: makePolicy(), etag: '"v1"' };

describe("syncPolicy", () => {
  it("asks for the policy with the key, and sends the tag it already has", async () => {
    const doFetch = vi.fn().mockResolvedValue(reply(304));

    await syncPolicy(config, stored, doFetch);

    const [url, init] = doFetch.mock.calls[0];
    expect(url).toBe("https://gov.example.com/api/v1/agent/policy");
    expect(init.headers).toEqual({ Authorization: "Bearer aigk_key", "If-None-Match": '"v1"' });
  });

  it("sends no tag when it has no policy to match it against", async () => {
    const doFetch = vi.fn().mockResolvedValue(reply(200, makePolicy(), { etag: '"v2"' }));

    await syncPolicy(config, { policy: null, etag: '"stale"' }, doFetch);

    expect(doFetch.mock.calls[0][1].headers).toEqual({ Authorization: "Bearer aigk_key" });
  });

  it("takes a new policy and its tag", async () => {
    const fresh = makePolicy({ unapproved_site_action: "block" });
    const doFetch = vi.fn().mockResolvedValue(reply(200, fresh, { etag: '"v2"' }));

    const result = await syncPolicy(config, stored, doFetch);

    expect(result.changed).toBe(true);
    expect(result.policy?.unapproved_site_action).toBe("block");
    expect(result.etag).toBe('"v2"');
    expect(result.status.kind).toBe("ok");
  });

  it("keeps the policy when nothing has changed", async () => {
    const result = await syncPolicy(config, stored, vi.fn().mockResolvedValue(reply(304)));

    expect(result).toMatchObject({ policy: stored.policy, etag: '"v1"', changed: false });
    expect(result.status.kind).toBe("unchanged");
  });

  it.each([
    ["the key is refused", reply(401), "rejected"],
    ["the key is locked out", reply(429), "rejected"],
    ["the server fails", reply(500), "error"],
    ["the address is wrong", reply(404), "error"],
  ])("keeps the last good policy when %s", async (_name, response, kind) => {
    const result = await syncPolicy(config, stored, vi.fn().mockResolvedValue(response));

    expect(result).toMatchObject({ policy: stored.policy, etag: '"v1"', changed: false });
    expect(result.status.kind).toBe(kind);
  });

  it("keeps the last good policy when the platform can't be reached", async () => {
    const result = await syncPolicy(config, stored, vi.fn().mockRejectedValue(new TypeError("offline")));

    expect(result).toMatchObject({ policy: stored.policy, changed: false });
    expect(result.status.kind).toBe("offline");
  });

  it("keeps the last good policy when the answer isn't a policy", async () => {
    for (const bad of [reply(200, { hello: "world" }), reply(200, "<html>proxy error</html>")]) {
      const result = await syncPolicy(config, stored, vi.fn().mockResolvedValue(bad));
      expect(result).toMatchObject({ policy: stored.policy, changed: false });
      expect(result.status.kind).toBe("error");
    }
    const unreadable = new Response("not json", { status: 200 });
    expect((await syncPolicy(config, stored, vi.fn().mockResolvedValue(unreadable))).status.kind).toBe("error");
  });

  it("has no policy to apply before it has ever had one", async () => {
    const result = await syncPolicy(config, { policy: null, etag: null }, vi.fn().mockResolvedValue(reply(401)));

    expect(result.policy).toBeNull();
    expect(result.changed).toBe(false);
  });
});

describe("flushEvents", () => {
  function filled(count = 2): EventBuffer {
    const buffer = new EventBuffer();
    for (let i = 0; i < count; i += 1) buffer.add(event({ domain: `site${i}.ai` }), i + 1);
    return buffer;
  }

  it("sends the counts, who they are for, and the key", async () => {
    const buffer = filled();
    const doFetch = vi.fn().mockResolvedValue(reply(202, { accepted: 2 }));

    const result = await flushEvents(config, "elena@example.com", buffer, doFetch);

    const [url, init] = doFetch.mock.calls[0];
    expect(url).toBe("https://gov.example.com/api/v1/agent/events");
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer aigk_key");
    const body = JSON.parse(init.body);
    expect(body.user_email).toBe("elena@example.com");
    expect(body.events).toEqual([
      { ...event({ domain: "site0.ai" }), count: 1 },
      { ...event({ domain: "site1.ai" }), count: 2 },
    ]);
    expect(Object.keys(body.events[0]).sort()).toEqual(
      ["action", "count", "day", "domain", "event_type", "rule_id"].sort(),
    );
    expect(result).toMatchObject({ sent: 2, dropped: 0 });
    expect(buffer.size).toBe(0);
  });

  it("does nothing when there is nothing to send", async () => {
    const doFetch = vi.fn();

    const result = await flushEvents(config, "a@b.co", new EventBuffer(), doFetch);

    expect(doFetch).not.toHaveBeenCalled();
    expect(result).toMatchObject({ sent: 0, dropped: 0 });
    expect(result.status.kind).toBe("ok");
  });

  it("sends a long backlog in requests the server will take", async () => {
    const buffer = filled(MAX_BATCH + 10);
    const doFetch = vi.fn().mockResolvedValue(reply(202, { accepted: 1 }));

    const result = await flushEvents(config, "a@b.co", buffer, doFetch);

    expect(doFetch).toHaveBeenCalledTimes(2);
    expect(JSON.parse(doFetch.mock.calls[0][1].body).events).toHaveLength(MAX_BATCH);
    expect(JSON.parse(doFetch.mock.calls[1][1].body).events).toHaveLength(10);
    expect(result.sent).toBe(MAX_BATCH + 10);
  });

  it.each([
    ["the platform can't be reached", () => Promise.reject(new TypeError("offline")), "offline"],
    ["the key is refused", () => Promise.resolve(reply(401)), "rejected"],
    ["the key is locked out", () => Promise.resolve(reply(429)), "rejected"],
    ["the server fails", () => Promise.resolve(reply(503)), "error"],
  ])("keeps every count when %s, and stops", async (_name, respond, kind) => {
    const buffer = filled(3);
    const doFetch = vi.fn().mockImplementation(respond);

    const result = await flushEvents(config, "a@b.co", buffer, doFetch);

    expect(result.sent).toBe(0);
    expect(result.status.kind).toBe(kind);
    expect(buffer.size).toBe(3);
    expect(doFetch).toHaveBeenCalledTimes(1);
  });

  it.each([400, 404, 422])("throws away a batch the platform refused for good (%i)", async (status) => {
    const buffer = filled(2);

    const result = await flushEvents(config, "a@b.co", buffer, vi.fn().mockResolvedValue(reply(status)));

    expect(result).toMatchObject({ sent: 0, dropped: 2 });
    expect(buffer.size).toBe(0);
  });

  it("goes on past a refused batch to the ones behind it", async () => {
    const buffer = filled(MAX_BATCH + 5);
    const doFetch = vi
      .fn()
      .mockResolvedValueOnce(reply(422))
      .mockResolvedValueOnce(reply(202, { accepted: 5 }));

    const result = await flushEvents(config, "a@b.co", buffer, doFetch);

    expect(result).toMatchObject({ sent: 5, dropped: MAX_BATCH });
    expect(buffer.size).toBe(0);
  });

  it("keeps the counts it hadn't reached when a later batch fails", async () => {
    const buffer = filled(MAX_BATCH + 5);
    const doFetch = vi
      .fn()
      .mockResolvedValueOnce(reply(202, { accepted: 1 }))
      .mockResolvedValueOnce(reply(500));

    const result = await flushEvents(config, "a@b.co", buffer, doFetch);

    expect(result.sent).toBe(MAX_BATCH);
    expect(buffer.size).toBe(5);
  });
});

describe("sendCheckin", () => {
  it("says who and which version, with the key, and nothing else", async () => {
    const doFetch = vi.fn().mockResolvedValue(reply(204));

    const sent = await sendCheckin(config, "elena@example.com", "1.2.0", doFetch);

    const [url, init] = doFetch.mock.calls[0];
    expect(url).toBe("https://gov.example.com/api/v1/agent/checkin");
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer aigk_key");
    expect(JSON.parse(init.body)).toEqual({ user_email: "elena@example.com", version: "1.2.0" });
    expect(sent).toBe(true);
  });

  it("reports failure, without throwing, when the platform refuses or can't be reached", async () => {
    expect(await sendCheckin(config, "a@b.co", "1.0.0", vi.fn().mockResolvedValue(reply(401)))).toBe(false);
    expect(await sendCheckin(config, "a@b.co", "1.0.0", vi.fn().mockRejectedValue(new TypeError("offline")))).toBe(false);
  });
});
