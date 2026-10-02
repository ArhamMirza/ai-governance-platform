import { useCurrentUser } from "../auth/hooks";
import { useLifecycle } from "../ai-systems/hooks";
import { useAuditLog } from "./hooks";

/**
 * Mirrors the backend's owner-stage approval rule for Risk/Impact
 * Assessments (risk_assessment_service.approve_owner_stage /
 * impact_assessment_service.approve_owner_stage): only the AI system's
 * current owner can approve this stage, and whoever most recently
 * submitted it can't be the one who approves it -- the same
 * self-submission check useCanApprove already does, just against a
 * specific person instead of a governance role.
 */
export function useCanApproveAsOwner(
  entityType: string,
  entityId: number,
  aiSystemRowId: number,
) {
  const { data: me } = useCurrentUser();
  const { data: lifecycle } = useLifecycle(aiSystemRowId);
  const { data: entries } = useAuditLog(entityType, entityId);

  const isOwner = me != null && lifecycle?.owner_id === me.id;
  const submissions = entries?.filter((entry) => entry.action === "submitted_for_review") ?? [];
  const lastSubmission = submissions.at(-1);
  const isSelfSubmission = me != null && lastSubmission?.actor_id === me.id;

  if (!isOwner) {
    return { canApprove: false, reason: "Only this AI system's owner can approve this stage." };
  }
  if (isSelfSubmission) {
    return { canApprove: false, reason: "A different user must approve this submission." };
  }
  return { canApprove: true, reason: null as string | null };
}
