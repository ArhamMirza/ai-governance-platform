// A real-browser test of the built extension: real Chrome or Edge, the real
// extension, a real running platform.
//
//   E2E_EMAIL=... E2E_PASSWORD=... node run.mjs [chrome|edge]
//
// See README.md for the setup. Needs a DEV build of the extension
// (DEV_CONFIG=1 npm run build in ..), because it gives the extension its
// settings through its own storage instead of the system's managed policy.
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import puppeteer from "puppeteer-core";

const label = process.argv[2] ?? "chrome";
const BROWSERS = {
  chrome: [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/usr/bin/google-chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ],
  edge: [
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/microsoft-edge",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  ],
};
const exe = process.env.BROWSER_EXE ?? (BROWSERS[label] ?? []).find((candidate) => fs.existsSync(candidate));
if (!exe) {
  console.error(`Could not find ${label}. Set BROWSER_EXE to its path.`);
  process.exit(2);
}
const extDir = path.resolve(process.env.EXTENSION_DIR ?? "../dist");
const adminEmail = process.env.E2E_EMAIL;
const adminPassword = process.env.E2E_PASSWORD;
if (!adminEmail || !adminPassword) {
  console.error("Set E2E_EMAIL and E2E_PASSWORD to a platform account that is the Chief AI Governance Officer.");
  process.exit(2);
}
if (!JSON.parse(fs.readFileSync(path.join(extDir, "manifest.json"), "utf8")).name.includes("(DEV)")) {
  console.error("The extension in " + extDir + " is not a DEV build. Run: DEV_CONFIG=1 npm run build");
  process.exit(2);
}
// The stub chat page, served over HTTPS under the AI sites' own names (the
// browser is told to map those names to this machine).
const stub = spawn(process.execPath, [path.resolve("stub-server.mjs")], { stdio: ["ignore", "pipe", "inherit"] });
await new Promise((resolve, reject) => {
  stub.stdout.on("data", (chunk) => String(chunk).includes("stub on") && resolve());
  stub.on("exit", (code) => reject(new Error(`stub server exited with ${code}`)));
});

const API = (process.env.PLATFORM_URL ?? "http://localhost:8000") + "/api/v1";
const PORT = 8766;
const shots = path.resolve("shots");
fs.mkdirSync(shots, { recursive: true });

const results = [];
function check(name, ok, detail = "") {
  results.push({ name, ok });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? `  -- ${detail}` : ""}`);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(fn, what, ms = 15000) {
  const end = Date.now() + ms;
  let last;
  while (Date.now() < end) {
    try {
      last = await fn();
      if (last) return last;
    } catch (e) {
      last = e;
    }
    await sleep(150);
  }
  throw new Error(`Timed out waiting for ${what}`);
}

// ---------- the platform ----------
const loginResponse = await fetch(`${API}/auth/login`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ email: adminEmail, password: adminPassword }),
});
const cookie = loginResponse.headers.getSetCookie().map((c) => c.split(";")[0]).join("; ");
async function platform(method, p, body) {
  const r = await fetch(API + p, {
    method,
    headers: { cookie, "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: r.status, body: r.status === 204 ? null : await r.json().catch(() => null) };
}
check("signed in to the platform as the CAIGO", loginResponse.status === 200);
await platform("PUT", "/ai-use/settings", { unapproved_site_action: "warn" });
const key = (await platform("POST", "/ai-use/enrollment-key")).body.key;
check("an enrollment key was issued", key.startsWith("aigk_"));

// ---------- the browser ----------
const flags = [
  "--no-first-run",
  "--no-default-browser-check",
  "--ignore-certificate-errors",
  "--disable-features=HttpsUpgrades,HttpsFirstBalancedModeAutoEnable",
  "--host-resolver-rules=" +
    ["chatgpt.com", "claude.ai", "grok.com", "copilot.microsoft.com", "chat.deepseek.com"]
      .map((h) => `MAP ${h} 127.0.0.1`)
      .join(","),
];
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "e2e-profile-"));
let browser;
let child = null;
let installedId = null;
if (label.startsWith("edge")) {
  // Puppeteer's own launcher can't start Edge here, so start it directly and attach.
  child = spawn(
    exe,
    ["--headless=new", "--remote-debugging-port=9335", `--user-data-dir=${profile}`, "--enable-unsafe-extension-debugging", ...flags, "about:blank"],
    { stdio: "ignore" },
  );
  await sleep(4000);
  browser = await puppeteer.connect({ browserURL: "http://127.0.0.1:9335", protocolTimeout: 30000 });
  installedId = await browser.installExtension(path.resolve(extDir));
} else {
  browser = await puppeteer.launch({
    executablePath: exe,
    headless: true,
    pipe: true,
    protocolTimeout: 30000,
    enableExtensions: [path.resolve(extDir)],
    userDataDir: profile,
    args: flags,
  });
}
const errors = [];
try {
  const target = await browser.waitForTarget(
    (t) => t.type() === "service_worker" && (installedId === null || t.url().includes(installedId)),
    { timeout: 20000 },
  );
  const sw = await target.worker();
  sw.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  const extId = new URL(target.url()).host;
  const swEval = (fn, arg) => sw.evaluate(fn, arg);
  const status = () => swEval(async () => (await chrome.storage.local.get("status")).status);

  // Unconfigured to start with.
  const before = await until(status, "the first status");
  check("starts unconfigured and says so", before.kind === "error" && /Not configured/.test(before.message), before.message);
  check("shows the warning badge when not connected", (await swEval(() => chrome.action.getBadgeText({}))) === "!");

  async function refreshNow() {
    const previous = (await status())?.at;
    await swEval(() => chrome.alarms.create("policy", { when: Date.now() + 50 }));
    await until(async () => (await status())?.at !== previous, "the policy to refresh", 20000);
    await sleep(400); // let the new rules finish applying
    return status();
  }
  async function setPlatformAction(action) {
    await platform("PUT", "/ai-use/settings", { unapproved_site_action: action });
    return refreshNow();
  }

  // ---------- connect ----------
  await swEval((cfg) => chrome.storage.local.set({ devConfig: cfg }), {
    serverUrl: process.env.PLATFORM_URL ?? "http://localhost:8000",
    portalUrl: "http://localhost:5173",
    enrollmentKey: key,
  });
  const connected = await until(async () => {
    const s = await status();
    return s.kind === "ok" ? s : null;
  }, "the extension to fetch its policy");
  check("fetches the policy from the real backend with its key", connected.kind === "ok" && connected.hasPolicy, connected.message);
  check("clears the warning badge once connected", (await swEval(() => chrome.action.getBadgeText({}))) === "");

  const stored = await swEval(async () => (await chrome.storage.local.get("policy")).policy);
  const policy = stored.policy;
  check("the stored policy has the tools and rules", policy.tools.length === 12 && policy.rules.length === 5, `${policy.tools.length} tools, ${policy.rules.length} rules`);
  check("keeps the tag for the next check", /^".+"$/.test(stored.etag ?? ""), stored.etag);

  const unapproved = policy.tools.filter((t) => t.status === "catalogued" || t.status === "revoked").flatMap((t) => t.domains);
  const rules = await swEval(() => chrome.declarativeNetRequest.getDynamicRules());
  check("installs a redirect rule for each unapproved domain (warn mode)", rules.length === unapproved.length && rules.length > 0, `${rules.length} rules`);
  check("redirect rules point into the extension", rules.every((r) => r.action.redirect.extensionPath.startsWith("/blocked.html?mode=") || r.action.redirect.extensionPath.includes("mode=warn")));
  const scripts = await swEval(() => chrome.scripting.getRegisteredContentScripts());
  check("registers the checking script", scripts.length === 1 && scripts[0].matches.includes("*://chatgpt.com/*"), `${scripts[0]?.matches.length} patterns`);
  check("registers it only for catalogued domains", scripts[0].matches.every((m) => /^\*:\/\/(\*\.)?[a-z0-9.-]+\/\*$/.test(m) && !m.startsWith("*://*/")));

  // ---------- an unapproved site: warn ----------
  const page = await browser.newPage();
  await page.setViewport({ width: 900, height: 700 });
  await page.goto(`https://claude.ai:${PORT}/`).catch(() => {});
  const warnUrl = new URL(page.url());
  check("an unapproved site is replaced by the extension's page (warn mode)", warnUrl.host === extId && warnUrl.pathname === "/blocked.html" && warnUrl.searchParams.get("mode") === "warn", page.url());
  const warnText = await page.$eval("main", (m) => m.innerText);
  check("the page names the tool and says it isn't approved", /Claude \(claude\.ai\)/.test(warnText) && /hasn't been approved/.test(warnText));
  const requestHref = await page.$eval("#request", (a) => a.href);
  check("offers to request the tool, filled in for the portal", requestHref === "http://localhost:5173/tools?name=Claude&domain=claude.ai", requestHref);
  check("offers to continue anyway in warn mode", !(await page.$eval("#continue", (b) => b.hidden)));
  await page.screenshot({ path: path.join(shots, `${label}-blocked-warn.png`) });

  await page.click("#continue");
  const allow = await until(async () => {
    const r = await swEval(() => chrome.declarativeNetRequest.getSessionRules());
    return r.length ? r : null;
  }, "the allow rule");
  check("continuing adds a temporary allow rule for that domain", allow[0].action.type === "allow" && allow[0].condition.requestDomains[0] === "claude.ai");
  await sleep(1500); // the click also starts a navigation to the site's real address
  const afterContinue = await browser.newPage();
  await afterContinue.goto(`https://claude.ai:${PORT}/`).catch(() => {});
  check("after continuing, the site loads instead of being redirected", afterContinue.url() === `https://claude.ai:${PORT}/`, afterContinue.url());
  await afterContinue.close();

  // ---------- block ----------
  await setPlatformAction("block");
  const blockRules = await swEval(() => chrome.declarativeNetRequest.getDynamicRules());
  check("a policy change reaches the browser's rules", blockRules.every((r) => r.action.redirect.extensionPath.includes("mode=block")));
  const page2 = await browser.newPage();
  await page2.goto(`https://grok.com:${PORT}/`).catch(() => {});
  const blockUrl = new URL(page2.url());
  check("block mode replaces the site with the blocked page", blockUrl.host === extId && blockUrl.searchParams.get("mode") === "block", page2.url());
  check("block mode offers no way to continue", await page2.$eval("#continue", (b) => b.hidden));
  await page2.screenshot({ path: path.join(shots, `${label}-blocked-block.png`) });

  // ---------- monitor ----------
  await setPlatformAction("monitor");
  const monitorRules = await swEval(() => chrome.declarativeNetRequest.getDynamicRules());
  check("monitor mode removes the redirect rules", monitorRules.length === 0);
  await swEval(() => chrome.declarativeNetRequest.updateSessionRules({ removeRuleIds: [5000, 5001, 5002, 5003, 5100, 5500, 5899] }));
  const grok = await browser.newPage();
  await grok.setViewport({ width: 900, height: 700 });
  await grok.goto(`https://grok.com:${PORT}/`);
  check("monitor mode lets an unapproved site load", grok.url() === `https://grok.com:${PORT}/`);

  // ---------- what goes in ----------
  async function typeAndEnter(p, text) {
    await p.click("#box");
    await p.keyboard.type(text);
    await p.keyboard.press("Enter");
    await sleep(500);
  }
  const logOf = (p) => p.$eval("#log", (e) => e.textContent);

  // an approved tool (cleared for internal data)
  const chat = await browser.newPage();
  await chat.setViewport({ width: 900, height: 700 });
  await chat.goto(`https://chatgpt.com:${PORT}/`);
  await sleep(1200); // the script registers at document_start; let it settle
  await typeAndEnter(chat, "Please summarise this article about gardening.");
  check("a clean message to an approved tool is sent", /^SENT: Please summarise/.test(await logOf(chat)), await logOf(chat));
  await typeAndEnter(chat, "see PROJ-1234 for details");
  check("internal data to a tool cleared for internal data is sent without a fuss", /^SENT: see PROJ-1234/.test(await logOf(chat)) && (await chat.evaluate(() => [...document.documentElement.children].filter((n) => n.tagName === "DIV" && !n.id).length)) === 0, await logOf(chat));

  // find a button inside the closed dialog through the debugger, then press it
  async function pressDialogButton(p, text) {
    const client = await p.createCDPSession();
    const { root } = await client.send("DOM.getDocument", { depth: -1, pierce: true });
    const find = (node) => {
      if (node.nodeName === "BUTTON" && (node.children ?? []).some((c) => c.nodeValue === text)) return node;
      for (const child of [...(node.children ?? []), ...(node.shadowRoots ?? []), ...(node.contentDocument ? [node.contentDocument] : [])]) {
        const hit = find(child);
        if (hit) return hit;
      }
      return null;
    };
    const button = find(root);
    if (!button) {
      await client.detach();
      return false;
    }
    const { model } = await client.send("DOM.getBoxModel", { backendNodeId: button.backendNodeId });
    const [x1, y1, , , x3, y3] = model.border;
    await p.mouse.click((x1 + x3) / 2, (y1 + y3) / 2);
    await client.detach();
    await sleep(400);
    return true;
  }
  const boxValue = (p) => p.$eval("#box", (b) => b.value);

  await chat.click("#box");
  await chat.keyboard.type("my card is 4111 1111 1111 1111");
  await chat.screenshot({ path: path.join(shots, `${label}-before-block.png`) });
  await chat.keyboard.press("Enter");
  await sleep(600);
  check("a card number to an approved tool is stopped on Enter", /^SENT: see PROJ-1234/.test(await logOf(chat)) && (await boxValue(chat)).includes("4111"), await logOf(chat));
  await chat.screenshot({ path: path.join(shots, `${label}-dialog-block.png`) });
  check("the refusal dialog has an OK button", await pressDialogButton(chat, "OK"));
  check("pressing OK leaves the message unsent in the box", (await boxValue(chat)).includes("4111"));
  await chat.evaluate(() => {
    document.getElementById("box").value = "";
  });
  await chat.click("#box");

  // a rule about data above what the tool is cleared for: a warning
  await chat.keyboard.type("Notes on Project Falcon");
  await chat.keyboard.press("Enter");
  await sleep(500);
  check("data above the tool's clearance raises a warning", /^SENT: see PROJ-1234/.test(await logOf(chat)) && (await boxValue(chat)) === "Notes on Project Falcon");
  await chat.screenshot({ path: path.join(shots, `${label}-dialog-warn.png`) });
  check("pressing Cancel keeps it from being sent", (await pressDialogButton(chat, "Cancel")) && /^SENT: see PROJ-1234/.test(await logOf(chat)));
  await chat.click("#box");
  await chat.keyboard.press("Enter");
  await sleep(500);
  check("pressing Send anyway sends it", (await pressDialogButton(chat, "Send anyway")) && /^SENT: Notes on Project Falcon/.test(await logOf(chat)), await logOf(chat));

  // an unapproved tool (held to every rule, as if cleared for public data only)
  await grok.bringToFront(); // a background tab doesn't render, so clicks wait forever
  await typeAndEnter(grok, "see PROJ-1234 for details");
  check("a monitored rule lets the message through on an unapproved tool", /^SENT: see PROJ-1234/.test(await logOf(grok)), await logOf(grok));
  await grok.click("#box");
  await grok.keyboard.type("my card is 4111 1111 1111 1111");
  await grok.click("#send");
  await sleep(500);
  check("a card number is stopped when the send button is clicked", /^SENT: see PROJ-1234/.test(await logOf(grok)) && (await boxValue(grok)).includes("4111"));
  check("and the dialog can be dismissed", await pressDialogButton(grok, "OK"));

  // ---------- the counts ----------
  const buffered = await swEval(async () => (await chrome.storage.local.get("events")).events);
  const bufferedText = JSON.stringify(buffered);
  check("counts are waiting to be sent", Array.isArray(buffered) && buffered.length >= 4, `${buffered?.length} counts`);
  check("the waiting counts hold no text from the page", !/4111|Falcon|PROJ-1234|gardening/.test(bufferedText));
  check("the counts hold only the allowed fields", buffered.every((e) => Object.keys(e).sort().join() === "action,count,day,domain,event_type,rule_id"));

  await swEval(() => chrome.alarms.create("flush", { when: Date.now() + 50 }));
  await until(
    async () => (await swEval(async () => (await chrome.storage.local.get("events")).events)).length === 0,
    "the extension to send its counts",
    20000,
  );
  const usage = (await platform("GET", "/ai-use/usage?days=7")).body;
  const flat = JSON.stringify(usage);
  check("the platform received the counts", usage.by_type.length >= 2, usage.by_type.map((t) => `${t.event_type}=${t.count}`).join(" "));
  check("a card number stopped on chatgpt.com is counted against the card rule", usage.by_rule.some((r) => r.rule_name === "Payment card numbers" && r.blocked >= 1));
  check("a client-name warning is counted against its rule", usage.by_rule.some((r) => /Client/.test(r.rule_name ?? "")), JSON.stringify(usage.by_rule));
  check("the platform's usage holds no text from the pages", !/4111|PROJ-1234|gardening/.test(flat));
  check("unidentified browser profiles are filed under the placeholder", usage.by_user.some((u) => u.user_ref === "unidentified@browser.invalid"), JSON.stringify(usage.by_user.map((u) => u.user_ref)));
  const left = await swEval(async () => (await chrome.storage.local.get("events")).events);
  check("the buffer is emptied once the platform has taken the counts", left.length === 0, JSON.stringify(left));

  // ---------- when the key stops working ----------
  await swEval((cfg) => chrome.storage.local.set({ devConfig: cfg }), {
    serverUrl: process.env.PLATFORM_URL ?? "http://localhost:8000",
    enrollmentKey: "aigk_not_the_key",
  });
  const refused = await until(async () => {
    const s = await status();
    return s.kind === "rejected" ? s : null;
  }, "the refusal to be noticed");
  check("a refused key is reported, not hidden", refused.kind === "rejected", refused.message);
  check("a refused key leaves the last good policy in force", refused.hasPolicy && (await swEval(() => chrome.scripting.getRegisteredContentScripts())).length === 1);
  check("a refused key keeps the warning badge up", (await swEval(() => chrome.action.getBadgeText({}))) === "!");

  check("the service worker logged no errors", errors.length === 0, errors.slice(0, 2).join(" | "));
} catch (e) {
  check(`the run completed (${e.message})`, false);
} finally {
  await browser.close().catch(() => {});
  child?.kill();
  stub.kill();
}

const failed = results.filter((r) => !r.ok);
console.log(`\n${label}: ${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
