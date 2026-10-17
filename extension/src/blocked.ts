/**
 * The page an unapproved AI site is replaced with. It says plainly what
 * happened and why, and offers the two ways forward: ask for the tool, or --
 * if the organization only warns -- carry on for an hour.
 */

import { parseConfig, requestUrl } from "./config.ts";
import type { ExtensionMessage } from "./messages.ts";

const params = new URLSearchParams(location.search);
const domain = params.get("domain") ?? "";
const tool = params.get("tool") ?? domain;
const mode = params.get("mode") === "warn" ? "warn" : "block";

function byId(id: string): HTMLElement {
  return document.getElementById(id) as HTMLElement;
}

async function send(message: ExtensionMessage): Promise<void> {
  try {
    await chrome.runtime.sendMessage(message);
  } catch {
    // The page still works if the count can't be recorded.
  }
}

byId("detail").textContent =
  mode === "block"
    ? `${tool} (${domain}) hasn't been approved for use at work, so it has been blocked.`
    : `${tool} (${domain}) hasn't been approved for use at work. You can still open it, but please don't put company or customer information into it.`;
document.title = `${tool} isn't approved`;

void send({ type: "interstitial", domain, mode });

void (async () => {
  let managed: Record<string, unknown> | null = null;
  try {
    managed = await chrome.storage.managed.get(null);
  } catch {
    managed = null;
  }
  const config = parseConfig(managed);

  const link = byId("request") as HTMLAnchorElement;
  if (config !== null) {
    link.href = requestUrl(config, tool, domain);
    link.hidden = false;
    link.addEventListener("click", () => void send({ type: "request", domain }));
  }

  if (mode === "warn") {
    const button = byId("continue") as HTMLButtonElement;
    button.hidden = false;
    button.addEventListener("click", async () => {
      button.disabled = true;
      // Wait for the allow rule to be in place before going there.
      await send({ type: "continue", domain });
      location.href = `https://${domain}/`;
    });
  }
})();
