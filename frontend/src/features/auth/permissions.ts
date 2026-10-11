/**
 * Mirrors the backend's role -> action table (app/core/permissions.py). The
 * server is the real enforcement point (every mutating request is checked
 * there regardless of what the UI shows) -- this exists purely so the UI can
 * proactively hide actions a role can't take, instead of letting someone
 * click a button that predictably 403s.
 */

export type Role = "admin" | "contributor" | "viewer" | "employee";

export type Action = "view" | "edit" | "approve" | "manage_users" | "manage_settings";

const ROLE_PERMISSIONS: Record<Role, ReadonlySet<Action>> = {
  viewer: new Set(["view"]),
  // An employee login reaches only the staff home, so it holds no action.
  employee: new Set(),
  contributor: new Set(["view", "edit"]),
  admin: new Set(["view", "edit", "approve", "manage_users", "manage_settings"]),
};

export function hasPermission(role: string | undefined, action: Action): boolean {
  if (!role || !(role in ROLE_PERMISSIONS)) return false;
  return ROLE_PERMISSIONS[role as Role].has(action);
}
