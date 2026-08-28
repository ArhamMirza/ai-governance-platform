import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { DataGrid } from "../../sheets/components/DataGrid";
import type { SelectOption } from "../../sheets/components/DataGrid";
import { dataInventoryAdapter } from "../api";

const QUERY_KEY = ["data-inventory"];
const LONG_TEXT_COLUMNS = [
  "data_acquisition",
  "data_quality_measures",
  "data_provenance",
  "data_preparation",
];

export function DataInventoryGrid() {
  const { data: inventory } = useAISystemInventoryRows();

  const aiSystemOptions: SelectOption[] = (inventory?.rows ?? []).map((row) => ({
    value: String(row.id),
    label: typeof row.data.name === "string" && row.data.name ? row.data.name : `System #${row.id}`,
  }));

  return (
    <DataGrid
      queryKey={QUERY_KEY}
      adapter={dataInventoryAdapter}
      longTextColumnKeys={LONG_TEXT_COLUMNS}
      selectOptions={{ ai_system_row_id: aiSystemOptions }}
    />
  );
}
