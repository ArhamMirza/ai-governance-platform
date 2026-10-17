/** The toolbar popup: is the extension connected, and how fresh is its policy. */

import { STATUS_KEY } from "./messages.ts";

interface Stored {
  kind: string;
  message: string;
  hasPolicy: boolean;
  at: string;
}

const state = document.getElementById("state") as HTMLElement;
const when = document.getElementById("when") as HTMLElement;

void chrome.storage.local.get(STATUS_KEY).then((stored) => {
  const status = stored[STATUS_KEY] as Stored | undefined;
  if (status === undefined) {
    state.textContent = "Not connected yet.";
    return;
  }
  const healthy = status.hasPolicy && (status.kind === "ok" || status.kind === "unchanged");
  state.textContent = healthy ? "Connected. Your organization's AI policy is in force." : status.message;
  if (healthy === false && status.hasPolicy) {
    state.textContent += " The last policy received is still being applied.";
  }
  when.textContent = `Last checked ${new Date(status.at).toLocaleString()}.`;
});
