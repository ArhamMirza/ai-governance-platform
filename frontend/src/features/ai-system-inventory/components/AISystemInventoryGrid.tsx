import { DataGrid } from "../../sheets/components/DataGrid";
import { aiSystemInventoryAdapter } from "../api";

const QUERY_KEY = ["ai-system-inventory"];
const LONG_TEXT_COLUMNS = ["description", "purpose"];

export function AISystemInventoryGrid() {
  return (
    <DataGrid
      queryKey={QUERY_KEY}
      adapter={aiSystemInventoryAdapter}
      longTextColumnKeys={LONG_TEXT_COLUMNS}
    />
  );
}
