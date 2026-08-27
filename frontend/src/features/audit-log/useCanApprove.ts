import { useCurrentUser } from "../auth/hooks";
import { hasPermission } from "../auth/permissions";
import { useAuditLog } from "./hooks";

/**
 * Mirrors the backend's segregation-of-duties rule (audit_service.
 * require_different_approver): whoever most recently submitted this entity
 * for review can't be the one who approves it. Computed from the same audit
 * log AuditLogViewer already renders, so no extra request.
 */
export function useCanApprove(entityType: string, entityId: number) {
  const { data: me } = useCurrentUser();
  const { data: entries } = useAuditLog(entityType, entityId);

  const hasRole = hasPermission(me?.role, "approve");
  const submissions = entries?.filter((entry) => entry.action === "submitted_for_review") ?? [];
  const lastSubmission = submissions.at(-1);
  const isSelfSubmission = me !== undefined && lastSubmission?.actor_id === me.id;

  if (!hasRole) return { canApprove: false, reason: "Only admins can approve." };
  if (isSelfSubmission) {
    return { canApprove: false, reason: "A different user must approve this submission." };
  }
  return { canApprove: true, reason: null as string | null };
}
