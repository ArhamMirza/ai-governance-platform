import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { DataGrid } from "../../sheets/components/DataGrid";
import type { SelectOption } from "../../sheets/components/DataGrid";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { dataInventoryAdapter } from "../api";
import { DatasetReviewActions } from "./DatasetReviewActions";

const QUERY_KEY = ["data-inventory"];
const LONG_TEXT_COLUMNS = [
  "data_acquisition",
  "data_quality_measures",
  "data_provenance",
  "data_preparation",
];

// Server-owned: the status only moves through the Data Owner / CAIGO review,
// so it is shown here rather than edited here.
const READ_ONLY_COLUMNS = ["approval_status"];

export function DataInventoryGrid() {
  const { data: inventory } = useAISystemInventoryRows();
  const { data: directory } = useUserDirectory();

  const aiSystemOptions: SelectOption[] = (inventory?.rows ?? []).map((row) => ({
    value: String(row.id),
    label: typeof row.data.name === "string" && row.data.name ? row.data.name : `System #${row.id}`,
  }));

  const ownerOptions: SelectOption[] = (directory ?? []).map((user) => ({
    value: String(user.id),
    label: formatUserOption(user),
  }));

  return (
    <DataGrid
      queryKey={QUERY_KEY}
      adapter={dataInventoryAdapter}
      longTextColumnKeys={LONG_TEXT_COLUMNS}
      readOnlyColumnKeys={READ_ONLY_COLUMNS}
      selectOptions={{ ai_system_row_id: aiSystemOptions, data_owner: ownerOptions }}
      rowActions={(row) => <DatasetReviewActions row={row} />}
      confirmDelete={(row) => {
        const name =
          typeof row.data.dataset_name === "string" && row.data.dataset_name
            ? row.data.dataset_name
            : "this dataset";
        return `Deleting ${name} also removes its review history. Any AI system relying on it for its Development stage gate will fall back to needing another approved dataset. This cannot be undone.`;
      }}
    />
  );
}
