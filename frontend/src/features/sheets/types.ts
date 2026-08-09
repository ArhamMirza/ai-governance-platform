export interface SheetColumn {
  key: string;
  label: string;
  data_type: string;
}

export interface SheetRow {
  id: number;
  sheet_id: number;
  row_index: number;
  data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SheetWithRows {
  id: number;
  entity_type: string;
  title: string;
  columns: SheetColumn[];
  rows: SheetRow[];
  created_at: string;
  updated_at: string;
}

/**
 * DataGrid doesn't know the URL shape of whatever it's rendering -- the AI
 * System Inventory (singleton) and a specific Risk Assessment (per-id) have
 * different endpoints. Each feature provides one of these instead.
 */
export interface SheetApiAdapter {
  get: () => Promise<SheetWithRows>;
  setColumns: (columns: SheetColumn[]) => Promise<SheetWithRows>;
  addRow: (data: Record<string, unknown>) => Promise<SheetRow>;
  updateRow: (rowId: number, data: Record<string, unknown>) => Promise<SheetRow>;
  deleteRow: (rowId: number) => Promise<void>;
  upload: (file: File) => Promise<SheetWithRows>;
  exportUrl: () => string;
}
