import { describe, expect, it } from "vitest";

import { decide } from "../src/decide.ts";
import {
  classify,
  hostMatches,
  parsePolicy,
  unapprovedDomains,
  watchedDomains,
} from "../src/policy.ts";
import { CARD, cardRule, clientRule, makePolicy, ticketRule, tool } from "./fixtures.ts";

describe("hostMatches", () => {
  it.each([
    ["chatgpt.com", "chatgpt.com", true],
    ["www.chatgpt.com", "chatgpt.com", true],
    ["a.b.chatgpt.com", "chatgpt.com", true],
    ["CHATGPT.COM", "chatgpt.com", true],
    ["chatgpt.com.", "chatgpt.com", true],
    ["notchatgpt.com", "chatgpt.com", false],
    ["chatgpt.com.evil.net", "chatgpt.com", false],
    ["evilchatgpt.com", "chatgpt.com", false],
    ["chatgpt.co", "chatgpt.com", false],
    ["openai.com", "chat.openai.com", false],
  ])("%s against %s", (host, domain, expected) => {
    expect(hostMatches(host, domain)).toBe(expected);
  });
});

describe("classify", () => {
  const policy = makePolicy();

  it("tells an unapproved tool, a limited one and an approved one apart", () => {
    expect(classify("chatgpt.com", policy)?.state).toBe("unapproved");
    expect(classify("claude.ai", policy)?.state).toBe("restricted");
    expect(classify("copilot.microsoft.com", policy)?.state).toBe("approved");
  });

  it("treats a tool whose access was withdrawn as unapproved", () => {
    expect(classify("grok.com", policy)?.state).toBe("unapproved");
  });

  it("finds a tool from a subdomain, and reports the catalogue's own domain", () => {
    const found = classify("www.chat.openai.com", policy);

    expect(found?.tool.name).toBe("ChatGPT");
    expect(found?.domain).toBe("chat.openai.com");
  });

  it("doesn't take a lookalike for the real thing", () => {
    for (const host of ["chatgpt.com.evil.net", "notchatgpt.com", "claude.ai.example.org"]) {
      expect(classify(host, policy), host).toBeNull();
    }
  });

  it("is null for a site that isn't an AI tool the organization knows", () => {
    expect(classify("example.com", policy)).toBeNull();
    expect(classify("", policy)).toBeNull();
  });

  it("prefers the most specific domain", () => {
    const nested = makePolicy({
      tools: [
        tool({ name: "Google", domains: ["google.com"], status: "approved" }),
        tool({ name: "Gemini", domains: ["gemini.google.com"], status: "catalogued" }),
      ],
    });

    expect(classify("gemini.google.com", nested)?.tool.name).toBe("Gemini");
    expect(classify("app.gemini.google.com", nested)?.tool.name).toBe("Gemini");
    expect(classify("mail.google.com", nested)?.tool.name).toBe("Google");
  });
});

describe("watchedDomains and unapprovedDomains", () => {
  it("lists every domain once", () => {
    const duplicated = makePolicy({
      tools: [tool(), tool({ name: "Again", domains: ["chatgpt.com"] })],
    });

    expect(watchedDomains(duplicated)).toEqual(["chatgpt.com", "chat.openai.com"]);
    expect(watchedDomains(makePolicy())).toEqual([
      "chatgpt.com",
      "chat.openai.com",
      "claude.ai",
      "copilot.microsoft.com",
      "grok.com",
    ]);
  });

  it("lists only the domains of tools nobody has approved", () => {
    expect(unapprovedDomains(makePolicy()).map((entry) => entry.domain)).toEqual([
      "chatgpt.com",
      "chat.openai.com",
      "grok.com",
    ]);
  });
});

describe("parsePolicy", () => {
  const valid = JSON.parse(JSON.stringify(makePolicy()));

  it("accepts a policy as the platform sends it", () => {
    expect(parsePolicy(valid)?.tools).toHaveLength(4);
  });

  it.each([
    ["nothing", null],
    ["text", "policy"],
    ["a list", []],
    ["no tools", { ...valid, tools: undefined }],
    ["no rules", { ...valid, rules: "none" }],
    ["an unknown site action", { ...valid, unapproved_site_action: "shrug" }],
    ["a tool with no name", { ...valid, tools: [{ ...valid.tools[0], name: 3 }] }],
    ["a tool with bad domains", { ...valid, tools: [{ ...valid.tools[0], domains: [1] }] }],
    ["a tool with an unknown status", { ...valid, tools: [{ ...valid.tools[0], status: "x" }] }],
    ["a rule with no id", { ...valid, rules: [{ ...valid.rules[0], id: "1" }] }],
    ["a rule with an unknown action", { ...valid, rules: [{ ...valid.rules[0], action: "x" }] }],
  ])("refuses %s", (_name, value) => {
    expect(parsePolicy(value)).toBeNull();
  });
});

describe("decide", () => {
  const policy = makePolicy();
  const text = `Project Falcon budget, card ${CARD}, ticket PROJ-1234`;

  it("has nothing to say about a site that isn't a catalogued AI tool", () => {
    expect(decide(text, "example.com", policy)).toBeNull();
    expect(decide(text, "chatgpt.com.evil.net", policy)).toBeNull();
  });

  it("holds an unapproved tool to every rule, and takes the strictest action", () => {
    const decision = decide(text, "chatgpt.com", policy)!;

    expect(decision.action).toBe("block");
    expect(decision.hits.map((hit) => hit.rule.id)).toEqual([cardRule.id, clientRule.id, ticketRule.id]);
    expect(decision.state).toBe("unapproved");
    expect(decision.domain).toBe("chatgpt.com");
    expect(decision.toolName).toBe("ChatGPT");
  });

  it("holds a limited tool only to rules about data above its clearance", () => {
    const decision = decide(text, "claude.ai", policy)!;

    expect(decision.hits.map((hit) => hit.rule.id)).toEqual([cardRule.id]);
    expect(decision.state).toBe("restricted");
  });

  it("holds a tool cleared for confidential data to nothing", () => {
    const decision = decide(text, "copilot.microsoft.com", policy)!;

    expect(decision.action).toBeNull();
    expect(decision.hits).toEqual([]);
    expect(decision.state).toBe("approved");
  });

  it("holds a tool whose access was withdrawn to the strictest standard, whatever it was once cleared for", () => {
    // The platform keeps the old clearance on a revoked tool; the extension must not honour it.
    const revoked = makePolicy({
      tools: [tool({ name: "Gone", domains: ["gone.ai"], status: "revoked", max_data_classification: "confidential" })],
    });

    const decision = decide(`card ${CARD}`, "gone.ai", revoked)!;

    expect(decision.state).toBe("unapproved");
    expect(decision.action).toBe("block");
  });

  it("finds nothing in clean text", () => {
    expect(decide("Please summarise this article.", "chatgpt.com", policy)?.action).toBeNull();
    expect(decide("", "chatgpt.com", policy)?.action).toBeNull();
  });

  it("acts on the strictest rule that applies, not the first", () => {
    const warnOnly = decide("Project Falcon and PROJ-1234", "chatgpt.com", policy)!;
    const monitorOnly = decide("see PROJ-1234", "chatgpt.com", policy)!;

    expect(warnOnly.action).toBe("warn");
    expect(monitorOnly.action).toBe("monitor");
  });
});
