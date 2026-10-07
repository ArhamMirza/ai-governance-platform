import { useAIRoles } from "../hooks";
import type { AIRole } from "../types";

interface AIRolePickerProps {
  /** Role codes currently held. */
  value: string[];
  onChange: (codes: string[]) => void;
  disabled?: boolean;
  /** Prefix for the checkbox ids, so two pickers on one page don't clash. */
  idPrefix: string;
}

/** The roles grouped under their main role, in the standard's order. */
function groupByParent(roles: AIRole[]): [string, AIRole[]][] {
  const groups = new Map<string, AIRole[]>();
  for (const role of roles) {
    groups.set(role.parent, [...(groups.get(role.parent) ?? []), role]);
  }
  return [...groups.entries()];
}

/** Checkboxes for the ISO/IEC 22989 AI roles an organization (or one AI
 * system) holds, grouped under AI provider / producer / customer / partner. */
export function AIRolePicker({ value, onChange, disabled, idPrefix }: AIRolePickerProps) {
  const { data: roles, isLoading, isError } = useAIRoles();

  if (isLoading) return <p>Loading AI roles...</p>;
  if (isError || !roles) return <p>Failed to load AI roles.</p>;

  const toggle = (code: string, held: boolean) =>
    onChange(held ? [...value, code] : value.filter((c) => c !== code));

  return (
    <div className="ai-role-picker">
      {groupByParent(roles).map(([parent, group]) => (
        <fieldset key={parent} disabled={disabled}>
          <legend>{parent}</legend>
          {group.map((role) => (
            <label key={role.code} htmlFor={`${idPrefix}-${role.code}`}>
              <input
                id={`${idPrefix}-${role.code}`}
                type="checkbox"
                checked={value.includes(role.code)}
                onChange={(e) => toggle(role.code, e.target.checked)}
              />
              {role.label} <span className="approval-note">{role.description}</span>
            </label>
          ))}
        </fieldset>
      ))}
    </div>
  );
}
