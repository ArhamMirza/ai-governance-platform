import { readError } from "../../../shared/api/readError";
import { useLifecycle, useSetAIRoles } from "../../ai-systems/hooks";
import { AIRoleChips } from "./AIRoleChips";
import { AIRolePicker } from "./AIRolePicker";

/** The AI roles for one AI system: by default the organization's, or its
 * own where it differs -- an organization can build one system and only
 * use another. */
export function AISystemAIRoles({ rowId }: { rowId: number }) {
  const { data: lifecycle, isLoading } = useLifecycle(rowId);
  const setRoles = useSetAIRoles(rowId);

  if (isLoading || !lifecycle) return <p>Loading AI roles...</p>;

  const hasOwn = lifecycle.ai_roles !== null;
  const disabled = setRoles.isPending || lifecycle.is_archived;
  const radioName = `ai-roles-source-${rowId}`;

  return (
    <div>
      <label>
        <input
          type="radio"
          name={radioName}
          checked={!hasOwn}
          disabled={disabled}
          onChange={() => setRoles.mutate({ ai_roles: null })}
        />
        Same as the organization
      </label>
      <label>
        <input
          type="radio"
          name={radioName}
          checked={hasOwn}
          disabled={disabled}
          // Starts from what it follows now, so setting its own is an edit
          // of the organization's roles rather than starting from nothing.
          onChange={() => setRoles.mutate({ ai_roles: lifecycle.effective_ai_roles })}
        />
        Set for this system
      </label>

      {hasOwn ? (
        <AIRolePicker
          idPrefix={`ai-system-${rowId}-role`}
          value={lifecycle.ai_roles ?? []}
          disabled={disabled}
          onChange={(codes) => setRoles.mutate({ ai_roles: codes })}
        />
      ) : (
        <AIRoleChips codes={lifecycle.effective_ai_roles} />
      )}
      {setRoles.isError && (
        <p role="alert">{readError(setRoles.error, "Failed to save the AI roles.")}</p>
      )}
    </div>
  );
}
