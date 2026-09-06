import type { DirectoryUser } from "./types";

/** How every owner/assessor picker in the app labels a directory entry --
 * one shared helper so the governance-role badge looks and behaves
 * identically everywhere instead of being reimplemented per field. */
export function formatUserOption(user: DirectoryUser): string {
  if (user.governance_roles.length === 0) return user.name;
  return `${user.name} (${user.governance_roles.join(", ")})`;
}
