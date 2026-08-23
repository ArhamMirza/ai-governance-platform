import { useRef, useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { useAddRow, useDeleteRow, useSetColumns, useSheet, useUpdateRow, useUploadSheet } from "../hooks";
import type { SheetApiAdapter, SheetRow } from "../types";

interface DataGridProps {
  queryKey: unknown[];
  adapter: SheetApiAdapter;
  readOnlyColumnKeys?: string[];
  isRowFlagged?: (row: SheetRow) => boolean;
  flaggedLabel?: string;
}

function cellText(value: unknown): string {
  return value !== undefined && value !== null ? String(value) : "";
}

export function DataGrid({
  queryKey,
  adapter,
  readOnlyColumnKeys = [],
  isRowFlagged,
  flaggedLabel = "Flagged",
}: DataGridProps) {
  const { data: sheet, isLoading, isError } = useSheet(queryKey, adapter);
  const setColumns = useSetColumns(queryKey, adapter);
  const addRow = useAddRow(queryKey, adapter);
  const updateRow = useUpdateRow(queryKey, adapter);
  const deleteRow = useDeleteRow(queryKey, adapter);
  const uploadSheet = useUploadSheet(queryKey, adapter);

  const [error, setError] = useState<string | null>(null);
  const [newColumnKey, setNewColumnKey] = useState("");
  const [newColumnLabel, setNewColumnLabel] = useState("");
  const [newRowDraft, setNewRowDraft] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (isLoading) return <p>Loading sheet...</p>;
  if (isError || !sheet) return <p>Failed to load sheet.</p>;

  const runMutation = async (action: () => Promise<unknown>, failureMessage: string) => {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : failureMessage);
    }
  };

  const handleAddColumn = () => {
    if (!newColumnKey.trim() || !newColumnLabel.trim()) return;
    runMutation(
      () =>
        setColumns.mutateAsync([
          ...sheet.columns,
          { key: newColumnKey.trim(), label: newColumnLabel.trim(), data_type: "text" },
        ]),
      "Failed to add column",
    ).then(() => {
      setNewColumnKey("");
      setNewColumnLabel("");
    });
  };

  const handleRemoveColumn = (key: string) =>
    runMutation(
      () => setColumns.mutateAsync(sheet.columns.filter((column) => column.key !== key)),
      "Failed to remove column",
    );

  const handleAddRow = () =>
    runMutation(() => addRow.mutateAsync(newRowDraft), "Failed to add row").then(() =>
      setNewRowDraft({}),
    );

  const handleDeleteRow = (rowId: number) =>
    runMutation(() => deleteRow.mutateAsync(rowId), "Failed to delete row");

  const handleCellBlur = (rowId: number, key: string, value: string) =>
    runMutation(() => updateRow.mutateAsync({ rowId, data: { [key]: value } }), "Failed to update cell");

  const handleUpload = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    runMutation(() => uploadSheet.mutateAsync(files[0]), "Failed to upload sheet").then(() => {
      if (fileInputRef.current) fileInputRef.current.value = "";
    });
  };

  return (
    <div>
      {error && <p role="alert">{error}</p>}

      <div className="grid-toolbar">
        <label htmlFor="grid-upload">Upload sheet</label>
        <input
          id="grid-upload"
          ref={fileInputRef}
          type="file"
          onChange={(e) => handleUpload(e.target.files)}
        />
        <a href={adapter.exportUrl()}>Export</a>
      </div>

      <div className="grid-toolbar">
        <input
          value={newColumnKey}
          onChange={(e) => setNewColumnKey(e.target.value)}
          placeholder="Column key"
          aria-label="New column key"
        />
        <input
          value={newColumnLabel}
          onChange={(e) => setNewColumnLabel(e.target.value)}
          placeholder="Column label"
          aria-label="New column label"
        />
        <button onClick={handleAddColumn}>Add Column</button>
      </div>

      <table>
        <thead>
          <tr>
            {sheet.columns.map((column) => (
              <th key={column.key}>
                {column.label}
                {!readOnlyColumnKeys.includes(column.key) && (
                  <button
                    onClick={() => handleRemoveColumn(column.key)}
                    aria-label={`Remove ${column.label}`}
                  >
                    ×
                  </button>
                )}
              </th>
            ))}
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sheet.rows.map((row) => {
            const flagged = isRowFlagged?.(row) ?? false;
            return (
              <tr key={row.id} className={flagged ? "row-flagged" : undefined}>
                {sheet.columns.map((column) => {
                  const isReadOnly = readOnlyColumnKeys.includes(column.key);
                  return (
                    <td key={column.key}>
                      {isReadOnly ? (
                        <span>{cellText(row.data[column.key])}</span>
                      ) : (
                        <input
                          aria-label={`${column.label} for row ${row.id}`}
                          defaultValue={cellText(row.data[column.key])}
                          onBlur={(e) => handleCellBlur(row.id, column.key, e.target.value)}
                        />
                      )}
                    </td>
                  );
                })}
                <td>
                  {flagged && <span className="flag-chip">{flaggedLabel}</span>}
                  <button onClick={() => handleDeleteRow(row.id)}>Delete</button>
                </td>
              </tr>
            );
          })}
          <tr>
            {sheet.columns.map((column) => (
              <td key={column.key}>
                {!readOnlyColumnKeys.includes(column.key) && (
                  <input
                    aria-label={`New row ${column.label}`}
                    value={newRowDraft[column.key] ?? ""}
                    onChange={(e) =>
                      setNewRowDraft({ ...newRowDraft, [column.key]: e.target.value })
                    }
                  />
                )}
              </td>
            ))}
            <td>
              <button onClick={handleAddRow}>Add Row</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
