import { Link } from "react-router-dom";

import { useGovernanceRoles } from "../../governance-roles/hooks";
import { useCompetenceRequirements } from "../hooks";
import { appliesToLabel, refreshLabel } from "../labels";

export function CompetenceRequirementList() {
  const { data: requirements, isLoading, isError } = useCompetenceRequirements();
  const { data: roles } = useGovernanceRoles();

  if (isLoading) return <p>Loading competence requirements...</p>;
  if (isError) return <p>Failed to load competence requirements.</p>;
  if (!requirements || requirements.length === 0) {
    return <p>No competence requirements yet.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Requirement</th>
          <th>Applies to</th>
          <th>Refresh</th>
          <th>Competent</th>
        </tr>
      </thead>
      <tbody>
        {requirements.map((requirement) => (
          <tr key={requirement.id} className={requirement.gap_count > 0 ? "row-flagged" : undefined}>
            <td>
              <Link to={`/competence/${requirement.id}`}>{requirement.title}</Link>
            </td>
            <td>{appliesToLabel(requirement.governance_role_id, roles)}</td>
            <td>{refreshLabel(requirement.refresh_interval_months)}</td>
            <td>
              {requirement.current_count} of {requirement.required_count}
              {requirement.gap_count > 0 && (
                <span className="flag-chip">{requirement.gap_count} outstanding</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
