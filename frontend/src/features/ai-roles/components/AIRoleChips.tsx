import { useAIRoles } from "../hooks";

/** The held roles as chips, labelled from the reference list. */
export function AIRoleChips({ codes }: { codes: string[] }) {
  const { data: roles } = useAIRoles();

  if (codes.length === 0) {
    return <p className="framework-tags-empty">No AI roles recorded.</p>;
  }

  const labelOf = (code: string) => roles?.find((role) => role.code === code)?.label ?? code;
  return (
    <ul className="framework-tag-chips">
      {codes.map((code) => (
        <li key={code} className="framework-tag-chip">
          {labelOf(code)}
        </li>
      ))}
    </ul>
  );
}
