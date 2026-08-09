import { DataGrid } from "../../sheets/components/DataGrid";
import { aiSystemInventoryAdapter } from "../api";

const QUERY_KEY = ["ai-system-inventory"];

export function AISystemInventoryGrid() {
  return <DataGrid queryKey={QUERY_KEY} adapter={aiSystemInventoryAdapter} />;
}
