import { DataGrid } from "../../sheets/components/DataGrid";
import { aiSystemInventoryAdapter } from "../api";

const QUERY_KEY = ["ai-system-inventory"];
const LONG_TEXT_COLUMNS = [
  "description",
  "purpose",
  "resource_documentation",
  "data_resources",
  "tooling_frameworks",
  "tooling_documentation",
  "compute_infrastructure",
  "hosting_environment",
  "development_team",
  "oversight_roles",
];

const COLUMN_GROUPS = [
  { label: "System Overview", keys: ["name", "description", "purpose", "lifecycle_stage", "risk_tier"] },
  { label: "Resource Documentation (A.4.2/A.4.3)", keys: ["resource_documentation", "data_resources"] },
  { label: "Tooling (A.4.4)", keys: ["tooling_frameworks", "tooling_documentation"] },
  { label: "System & Computing (A.4.5)", keys: ["compute_infrastructure", "hosting_environment"] },
  { label: "Human Resources (A.4.6)", keys: ["development_team", "oversight_roles"] },
];

export function AISystemInventoryGrid() {
  return (
    <DataGrid
      queryKey={QUERY_KEY}
      adapter={aiSystemInventoryAdapter}
      longTextColumnKeys={LONG_TEXT_COLUMNS}
      columnGroups={COLUMN_GROUPS}
    />
  );
}
