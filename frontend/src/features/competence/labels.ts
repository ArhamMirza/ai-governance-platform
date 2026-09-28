import type { GovernanceRole } from "../governance-roles/types";

export function appliesToLabel(
  roleId: number | null,
  roles: GovernanceRole[] | undefined,
): string {
  if (roleId === null) return "Everyone";
  return roles?.find((role) => role.id === roleId)?.name ?? `Role #${roleId}`;
}

export function refreshLabel(months: number | null): string {
  if (months === null) return "Once";
  return months === 1 ? "Every month" : `Every ${months} months`;
}
