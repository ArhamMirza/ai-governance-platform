// Checks that the built index.html can be served under a strict
// Content-Security-Policy (script-src 'self'): no inline scripts, no inline
// event handlers, no javascript: URLs, and no scripts from other sites.
//
//   node scripts/csp-check.mjs dist/index.html
//
// Run in CI after the build, so a change that quietly breaks the policy
// (a new inline snippet, a CDN script) fails the build instead of shipping.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/** What would be blocked by `script-src 'self'`, as a list of messages. */
export function findProblems(html) {
  const problems = [];

  for (const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
    const attributes = match[1];
    const body = match[2];
    const src = /\bsrc\s*=\s*["']?([^"'\s>]+)/i.exec(attributes);
    if (!src) {
      problems.push(`inline <script>${body.trim() ? ` (${body.trim().slice(0, 40)}...)` : ""}`);
    } else if (/^(?:[a-z][a-z0-9+.-]*:)?\/\//i.test(src[1])) {
      problems.push(`script from another site: ${src[1]}`);
    }
  }

  for (const match of html.matchAll(/<[a-z][^>]*\s(on[a-z]+)\s*=/gi)) {
    problems.push(`inline event handler: ${match[1]}`);
  }

  if (/(?:href|src|action|formaction)\s*=\s*["']?\s*javascript:/i.test(html)) {
    problems.push("a javascript: URL");
  }

  return problems;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const file = process.argv[2] ?? "dist/index.html";
  const problems = findProblems(readFileSync(file, "utf8"));
  if (problems.length > 0) {
    console.error(`${file} would be blocked by a strict Content-Security-Policy:`);
    for (const problem of problems) console.error(`  - ${problem}`);
    process.exit(1);
  }
  console.log(`${file}: ready for script-src 'self'.`);
}
