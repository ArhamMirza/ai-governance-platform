import { useState } from "react";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { GovernanceRoleList } from "../features/governance-roles/components/GovernanceRoleList";
import { OrgChart } from "../features/governance-roles/components/OrgChart";

type Tab = "roles" | "org-chart";

export function GovernanceRolesPage() {
  const [tab, setTab] = useState<Tab>("roles");
  const { data: me } = useCurrentUser();
  const canManage = hasPermission(me?.role, "manage_users");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Roles &amp; Responsibilities</h1>
          <p>
            Who is organizationally accountable for what, separate from technical permissions.
            {canManage
              ? " Add roles, assign people, and shape the reporting structure below."
              : " Visible to everyone so accountability is traceable."}
          </p>
        </div>
      </div>

      <div className="tab-bar">
        <button
          className={tab === "roles" ? "active" : undefined}
          onClick={() => setTab("roles")}
        >
          Roles &amp; Assignments
        </button>
        <button
          className={tab === "org-chart" ? "active" : undefined}
          onClick={() => setTab("org-chart")}
        >
          Org Chart
        </button>
      </div>

      {tab === "roles" && <GovernanceRoleList canManage={canManage} />}
      {tab === "org-chart" && <OrgChart canManage={canManage} />}
    </section>
  );
}
