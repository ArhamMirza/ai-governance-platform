/**
 * What IT gives each browser through managed storage (the enterprise policy
 * that force-installs the extension): where the platform is, where staff
 * request tools, and the enrollment key. Nothing here is entered by the user.
 */

export interface Config {
  /** The platform's API root, no trailing slash: https://governance.example.com */
  serverUrl: string;
  /** Where the employee portal is, for "request this tool". Defaults to the server. */
  portalUrl: string;
  enrollmentKey: string;
}

/** Plain http is for a developer's own machine only. */
function acceptableUrl(value: string): string | null {
  try {
    const url = new URL(value);
    const local = url.hostname === "localhost" || url.hostname === "127.0.0.1";
    if (url.protocol === "https:" || (url.protocol === "http:" && local)) {
      return value.replace(/\/+$/, "");
    }
  } catch {
    // fall through
  }
  return null;
}

/**
 * The configuration if managed storage holds a usable one, else null -- in
 * which case the extension does nothing and says it isn't configured.
 */
export function parseConfig(managed: Record<string, unknown> | null | undefined): Config | null {
  if (!managed) return null;
  const server = typeof managed.serverUrl === "string" ? acceptableUrl(managed.serverUrl.trim()) : null;
  const key = typeof managed.enrollmentKey === "string" ? managed.enrollmentKey.trim() : "";
  if (server === null || key === "") return null;
  const portal =
    typeof managed.portalUrl === "string" ? acceptableUrl(managed.portalUrl.trim()) : null;
  return { serverUrl: server, portalUrl: portal ?? server, enrollmentKey: key };
}

/** The address an unidentified profile's counts are filed under, so they still arrive. */
export const UNIDENTIFIED_USER = "unidentified@browser.invalid";

export function reportingEmail(profileEmail: string | null | undefined): string {
  const email = (profileEmail ?? "").trim().toLowerCase();
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) ? email : UNIDENTIFIED_USER;
}

/** Where a person goes to ask for a tool. */
export function requestUrl(config: Config, toolName: string, domain: string): string {
  const query = new URLSearchParams({ name: toolName, domain });
  return `${config.portalUrl}/tools?${query.toString()}`;
}
