/**
 * Light / dark preference.
 *
 * The stylesheet already defines all three states: `:root` carries the light
 * palette, a `prefers-color-scheme: dark` block guarded by
 * `:root:not([data-theme="light"])` covers "follow the OS", and
 * `:root[data-theme="dark"]` covers an explicit choice. So all this has to do
 * is set or clear one attribute on the root element -- "system" is the
 * absence of the attribute, not a third palette.
 */

export type ThemePreference = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "governance.theme";

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === "system" || value === "light" || value === "dark";
}

/** Storage throws in a private window or with site data blocked, and the app
 * must still render -- an unreadable preference just means "follow the OS". */
export function readStoredTheme(): ThemePreference {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return isThemePreference(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

export function storeTheme(preference: ThemePreference): void {
  try {
    if (preference === "system") localStorage.removeItem(THEME_STORAGE_KEY);
    else localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    // A preference that cannot be saved still applies for this session.
  }
}

export function applyTheme(preference: ThemePreference): void {
  const root = document.documentElement;
  if (preference === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", preference);
}
