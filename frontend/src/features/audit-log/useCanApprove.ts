import { useCurrentUser } from "../auth/hooks";
import { useCaigoDelegation } from "../governance-roles/hooks";
import { useUserDirectory } from "../users/hooks";
import { useAuditLog } from "./hooks";

const CHIEF_AI_GOVERNANCE_OFFICER = "Chief AI Governance Officer";

/**
 * Mirrors the backend's approval rule for Policy/Procedure and AI System
 * deployment/retirement: only the Chief AI Governance Officer can approve
 * (governance_role_service.require_caigo), and whoever most recently
 * submitted this entity for review can't be the one who approves it
 * (audit_service.require_different_approver). Computed from the same
 * user directory and audit log already fetched elsewhere, so no extra
 * request beyond what the page already loads.
 *
 * require_caigo's is_caigo check treats a time-boxed backup approver as
 * CAIGO too -- this used to check only the directory's governance_roles
 * list, which only ever names the actual role holder, so a real delegate's
 * Approve button silently never appeared even though the API would have
 * accepted their approval. useCaigoDelegation's GET is open to any
 * authenticated user (only setting/revoking it is admin-only), so this
 * costs nothing beyond what the page already has permission to read.
 */
export function useCanApprove(entityType: string, entityId: number) {
  const { data: me } = useCurrentUser();
  const { data: directory } = useUserDirectory();
  const { data: entries } = useAuditLog(entityType, entityId);
  const { data: delegation } = useCaigoDelegation();

  const myDirectoryEntry = directory?.find((user) => user.id === me?.id);
  const holdsCaigo =
    myDirectoryEntry?.governance_roles.includes(CHIEF_AI_GOVERNANCE_OFFICER) ?? false;
  const isActiveDelegate = me != null && delegation?.delegate_user_id === me.id;
  const isCaigo = holdsCaigo || isActiveDelegate;
  const submissions = entries?.filter((entry) => entry.action === "submitted_for_review") ?? [];
  const lastSubmission = submissions.at(-1);
  const isSelfSubmission = me != null && lastSubmission?.actor_id === me.id;

  if (!isCaigo) {
    return { canApprove: false, reason: "Only the Chief AI Governance Officer can approve." };
  }
  if (isSelfSubmission) {
    return { canApprove: false, reason: "A different user must approve this submission." };
  }
  return { canApprove: true, reason: null as string | null };
}
