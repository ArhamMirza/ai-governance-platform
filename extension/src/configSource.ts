/**
 * Where the extension's settings come from.
 *
 * In a real deployment, only from managed storage: the enterprise policy IT
 * pushes. Nobody using the browser can change it, which is the point.
 *
 * A development build (DEV_CONFIG=1 npm run build) also reads a `devConfig`
 * value from the extension's own storage, so it can be tried on a laptop
 * without editing system policy. In every other build the switch is a
 * constant `false` fixed when the extension is built, so the code reading
 * `devConfig` never runs: a deployed extension can't be pointed at another
 * server by writing to its storage. (The tests check exactly that.)
 */

import { type Config, parseConfig } from "./config.ts";

declare const __DEV_CONFIG__: boolean | undefined;

export const DEV_CONFIG_KEY = "devConfig";

export const devConfigEnabled = (): boolean =>
  typeof __DEV_CONFIG__ !== "undefined" && __DEV_CONFIG__ === true;

export async function loadConfig(): Promise<Config | null> {
  if (devConfigEnabled()) {
    const stored = (await chrome.storage.local.get(DEV_CONFIG_KEY))[DEV_CONFIG_KEY];
    const dev = parseConfig(stored as Record<string, unknown> | undefined);
    if (dev !== null) return dev;
  }
  try {
    return parseConfig(await chrome.storage.managed.get(null));
  } catch {
    // No managed storage at all -- the extension was loaded by hand.
    return null;
  }
}
