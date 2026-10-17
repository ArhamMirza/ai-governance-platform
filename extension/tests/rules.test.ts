import { describe, expect, it } from "vitest";

import {
  ALLOW_RULE_ID_BASE,
  REDIRECT_RULE_ID_BASE,
  allowRule,
  blockedPagePath,
  contentScriptMatches,
  redirectRules,
} from "../src/rules.ts";
import { makePolicy, tool } from "./fixtures.ts";

describe("redirectRules", () => {
  const policy = makePolicy();

  it("redirects nothing in monitor mode, which only counts", () => {
    expect(redirectRules(policy, "monitor", "/blocked.html")).toEqual([]);
  });

  it.each(["warn", "block"] as const)("redirects each unapproved domain in %s mode", (mode) => {
    const rules = redirectRules(policy, mode, "/blocked.html");

    expect(rules.map((rule) => rule.condition.requestDomains[0])).toEqual([
      "chatgpt.com",
      "chat.openai.com",
      "grok.com",
    ]);
    for (const rule of rules) {
      expect(rule.action.type).toBe("redirect");
      expect(rule.condition.resourceTypes).toEqual(["main_frame"]);
      expect(rule.action.redirect.extensionPath).toContain(`mode=${mode}`);
      expect(rule.action.redirect.extensionPath.startsWith("/blocked.html?")).toBe(true);
    }
  });

  it("never redirects an approved or limited tool", () => {
    const domains = redirectRules(policy, "block", "/blocked.html").flatMap(
      (rule) => rule.condition.requestDomains,
    );

    expect(domains).not.toContain("claude.ai");
    expect(domains).not.toContain("copilot.microsoft.com");
  });

  it("gives each rule its own id, from the range we own", () => {
    const ids = redirectRules(policy, "block", "/blocked.html").map((rule) => rule.id);

    expect(ids).toEqual([REDIRECT_RULE_ID_BASE, REDIRECT_RULE_ID_BASE + 1, REDIRECT_RULE_ID_BASE + 2]);
    expect(Math.max(...ids)).toBeLessThan(ALLOW_RULE_ID_BASE);
  });

  it("has nothing to redirect when every tool is approved", () => {
    const approved = makePolicy({ tools: [tool({ status: "approved" })] });

    expect(redirectRules(approved, "block", "/blocked.html")).toEqual([]);
  });
});

describe("blockedPagePath", () => {
  it("carries the domain, tool and mode, safely encoded", () => {
    const path = blockedPagePath("/blocked.html", "chat.example.ai", "Chat & Co <b>", "warn");
    const query = new URLSearchParams(path.split("?")[1]);

    expect(query.get("domain")).toBe("chat.example.ai");
    expect(query.get("tool")).toBe("Chat & Co <b>");
    expect(query.get("mode")).toBe("warn");
    expect(path).not.toContain("<b>");
  });
});

describe("allowRule", () => {
  it("outranks the redirect it overrides, in its own id range", () => {
    const [redirect] = redirectRules(makePolicy(), "warn", "/blocked.html");
    const allow = allowRule(7, "chatgpt.com");

    expect(allow.priority).toBeGreaterThan(redirect.priority);
    expect(allow.id).toBe(ALLOW_RULE_ID_BASE + 7);
    expect(allow.action).toEqual({ type: "allow" });
    expect(allow.condition.requestDomains).toEqual(["chatgpt.com"]);
  });
});

describe("contentScriptMatches", () => {
  it("covers the catalogued domains and their subdomains, and nothing else", () => {
    const matches = contentScriptMatches(makePolicy());

    expect(matches).toContain("*://chatgpt.com/*");
    expect(matches).toContain("*://*.chatgpt.com/*");
    expect(matches).toContain("*://*.claude.ai/*");
    expect(matches).toHaveLength(10);
    expect(matches.some((pattern) => pattern.includes("<all_urls>") || pattern === "*://*/*")).toBe(false);
  });

  it("lists a shared domain once", () => {
    const shared = makePolicy({
      tools: [tool(), tool({ name: "Again", domains: ["chatgpt.com"] })],
    });

    expect(contentScriptMatches(shared).filter((m) => m === "*://chatgpt.com/*")).toHaveLength(1);
  });

  it("is empty when there are no tools", () => {
    expect(contentScriptMatches(makePolicy({ tools: [] }))).toEqual([]);
  });
});
