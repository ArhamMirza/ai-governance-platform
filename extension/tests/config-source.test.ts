import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEV_CONFIG_KEY, devConfigEnabled, loadConfig } from "../src/configSource.ts";

const managed = { serverUrl: "https://managed.example.com", enrollmentKey: "managed-key" };
const dev = { serverUrl: "http://localhost:8000", enrollmentKey: "dev-key" };

function fakeChrome(options: { managed?: unknown; local?: Record<string, unknown>; managedThrows?: boolean }) {
  vi.stubGlobal("chrome", {
    storage: {
      managed: {
        get: async () => {
          if (options.managedThrows) throw new Error("no managed storage");
          return options.managed ?? {};
        },
      },
      local: { get: async (key: string) => ({ [key]: options.local?.[key] }) },
    },
  });
}

beforeEach(() => vi.unstubAllGlobals());
afterEach(() => vi.unstubAllGlobals());

describe("in a normal build", () => {
  it("is not a development build", () => {
    expect(devConfigEnabled()).toBe(false);
  });

  it("takes its settings from managed storage", async () => {
    fakeChrome({ managed });

    expect(await loadConfig()).toMatchObject({ serverUrl: "https://managed.example.com", enrollmentKey: "managed-key" });
  });

  it("ignores a development setting written to its own storage", async () => {
    fakeChrome({ managed, local: { [DEV_CONFIG_KEY]: dev } });

    expect(await loadConfig()).toMatchObject({ serverUrl: "https://managed.example.com" });
  });

  it("can't be pointed at another server by local storage when nothing is managed", async () => {
    fakeChrome({ managed: {}, local: { [DEV_CONFIG_KEY]: dev } });

    expect(await loadConfig()).toBeNull();
  });

  it("is unconfigured, not broken, when there is no managed storage at all", async () => {
    fakeChrome({ managedThrows: true });

    expect(await loadConfig()).toBeNull();
  });
});

describe("in a development build", () => {
  beforeEach(() => vi.stubGlobal("__DEV_CONFIG__", true));

  it("knows it is one", () => {
    expect(devConfigEnabled()).toBe(true);
  });

  it("prefers the development setting", async () => {
    fakeChrome({ managed, local: { [DEV_CONFIG_KEY]: dev } });

    expect(await loadConfig()).toMatchObject({ serverUrl: "http://localhost:8000", enrollmentKey: "dev-key" });
  });

  it("falls back to managed storage when there is no usable development setting", async () => {
    fakeChrome({ managed, local: { [DEV_CONFIG_KEY]: { serverUrl: "nonsense" } } });
    expect(await loadConfig()).toMatchObject({ serverUrl: "https://managed.example.com" });

    fakeChrome({ managed });
    expect(await loadConfig()).toMatchObject({ serverUrl: "https://managed.example.com" });
  });
});
