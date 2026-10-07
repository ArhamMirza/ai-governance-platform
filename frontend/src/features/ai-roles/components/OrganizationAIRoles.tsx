import { readError } from "../../../shared/api/readError";
import { useUpdateOrganizationContext } from "../../organization-context/hooks";
import type { OrganizationContext } from "../../organization-context/types";
import { AIRolePicker } from "./AIRolePicker";

/** The organization's own AI roles (ISO/IEC 22989) -- clause 4.1 has it
 * determine its role in relation to its AI systems. Saved as each is
 * ticked; part of the approved context, so changing them withdraws the
 * approval like any other edit to it. */
export function OrganizationAIRoles({ context }: { context: OrganizationContext }) {
  const update = useUpdateOrganizationContext();

  return (
    <section>
      <h3>Our AI Roles</h3>
      <p className="approval-note">
        What your organization does in relation to AI, in the terms of ISO/IEC 22989. Choose every
        one that applies; an AI system can narrow this on its own page.
      </p>
      <AIRolePicker
        idPrefix="org-ai-role"
        value={context.ai_roles}
        disabled={update.isPending}
        onChange={(codes) => update.mutate({ ai_roles: codes })}
      />
      {update.isError && (
        <p role="alert">{readError(update.error, "Failed to save the AI roles.")}</p>
      )}
    </section>
  );
}
