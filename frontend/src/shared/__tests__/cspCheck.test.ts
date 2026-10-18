// Vite's raw import, as in theme.test.ts: this project has no Node type definitions.
import { describe, expect, it } from "vitest";

import { findProblems } from "../../../scripts/csp-check.mjs";
import source from "../../../index.html?raw";

const page = (body: string) => `<!doctype html><html><head>${body}</head><body></body></html>`;

describe("csp-check", () => {
  it("accepts scripts loaded from the page's own origin", () => {
    const html = page(
      '<script src="/theme-init.js"></script><script type="module" crossorigin src="/assets/index-abc.js"></script>',
    );

    expect(findProblems(html)).toEqual([]);
  });

  it("flags an inline script and quotes the start of it", () => {
    const problems = findProblems(page("<script>window.x = 1;</script>"));

    expect(problems).toHaveLength(1);
    expect(problems[0]).toContain("inline <script>");
    expect(problems[0]).toContain("window.x = 1;");
  });

  it("flags an inline script even when it has a type", () => {
    expect(findProblems(page('<script type="module">import("/a.js")</script>'))).toHaveLength(1);
  });

  it("flags an empty script tag with no source", () => {
    expect(findProblems(page("<script></script>"))).toEqual(["inline <script>"]);
  });

  it.each([
    ["https://cdn.example.com/lib.js"],
    ["http://cdn.example.com/lib.js"],
    ["//cdn.example.com/lib.js"],
  ])("flags a script from another site: %s", (src) => {
    const problems = findProblems(page(`<script src="${src}"></script>`));

    expect(problems).toEqual([`script from another site: ${src}`]);
  });

  it("flags inline event handlers", () => {
    const problems = findProblems(page('<body onload="init()"><img src="a.png" onerror=bad()>'));

    expect(problems).toEqual(["inline event handler: onload", "inline event handler: onerror"]);
  });

  it("does not mistake an attribute whose name merely contains 'on' for a handler", () => {
    expect(findProblems(page('<meta name="description" content="one on one">'))).toEqual([]);
  });

  it("flags javascript: URLs", () => {
    expect(findProblems(page('<a href="javascript:alert(1)">x</a>'))).toEqual(["a javascript: URL"]);
  });

  it("allows inline styles, which the policy permits", () => {
    expect(findProblems(page("<style>body{margin:0}</style>"))).toEqual([]);
  });

  it("passes the real page source, so the theme script stays a file", () => {
    expect(findProblems(source)).toEqual([]);
    expect(source).toContain('src="/theme-init.js"');
  });
});
