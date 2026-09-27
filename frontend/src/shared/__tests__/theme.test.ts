import { describe, expect, it } from "vitest";

// Vite's raw-import suffix, not Node's fs -- this file has no Node type
// definitions available (tsconfig.app.json restricts "types" to
// ["vite/client"] only), and reading it through Vite keeps the test inside
// the same bundler-aware toolchain the app itself runs on.
import html from "../../../index.html?raw";
import { isThemePreference, THEME_STORAGE_KEY } from "../theme";

/**
 * index.html carries a pre-paint inline script that has to agree with this
 * module on the storage key and the two persisted preference values ("light"
 * and "dark" -- "system" is never written, see storeTheme) -- it runs before
 * any bundle loads, so it can't import theme.ts and has to duplicate that
 * contract by hand instead.
 *
 * Nothing at build time ties the two together, so this test is the one
 * thing that would catch them drifting apart: if THEME_STORAGE_KEY or the
 * set of stored preferences ever changes here without index.html's script
 * being updated to match, the pre-paint script would silently stop
 * recognising a stored preference and the flash-of-wrong-theme it exists to
 * prevent would come back for whichever value it no longer matches.
 */
describe("the pre-paint script in index.html", () => {
  it("reads the same storage key theme.ts writes", () => {
    expect(html).toContain(`localStorage.getItem("${THEME_STORAGE_KEY}")`);
  });

  it("recognises exactly the preferences theme.ts actually persists", () => {
    const persisted = (["light", "dark", "system"] as const).filter(
      (value) => isThemePreference(value) && value !== "system",
    );

    for (const value of persisted) {
      expect(html).toContain(`"${value}"`);
    }
    // "system" is never written to storage (storeTheme removes the key
    // instead) -- if the script started checking for it as a stored value,
    // that would itself be a sign the two have drifted apart.
    expect(html).not.toMatch(/t === "system"/);
  });
});
