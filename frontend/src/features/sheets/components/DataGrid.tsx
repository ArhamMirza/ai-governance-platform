import { useRef, useState } from "react";
import type { ReactNode } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { ConfirmDialog } from "../../../shared/components/ConfirmDialog";
import { useAddRow, useDeleteRow, useSetColumns, useSheet, useUpdateRow, useUploadSheet } from "../hooks";
import type { SheetApiAdapter, SheetRow } from "../types";

export interface SelectOption {
  value: string;
  label: string;
}

interface DataGridProps {
  queryKey: unknown[];
  adapter: SheetApiAdapter;
  readOnlyColumnKeys?: string[];
  isRowFlagged?: (row: SheetRow) => boolean;
  flaggedLabel?: string;
  /** Render a specific column as a <select> instead of a free-text input --
   * e.g. a risk owner picked from real users rather than typed free text. */
  selectOptions?: Record<string, SelectOption[]>;
  /** Extra per-row controls in the Actions cell, alongside Delete -- e.g. a
   * "Manage evidence" button. DataGrid stays unaware of what it does. */
  rowActions?: (row: SheetRow) => ReactNode;
  /** Columns holding a sentence rather than a label. These render as a
   * wrapping textarea so the whole value is readable -- a single-line input
   * silently truncates anything longer than the column. */
  longTextColumnKeys?: string[];
  /** Visually groups columns under a shared header row (e.g. "Tooling",
   * "Human Resources") -- purely presentational, does not change the
   * underlying column keys or data. Any column not listed in a group gets a
   * blank cell in the group row so headers stay aligned. */
  columnGroups?: { label: string; keys: string[] }[];
  /** Return the confirmation text for deleting a row, to require an explicit
   * confirm first. Omit to delete immediately. */
  confirmDelete?: (row: SheetRow) => string;
}

function cellText(value: unknown): string {
  return value !== undefined && value !== null ? String(value) : "";
}

interface GroupHeaderCell {
  label: string | null;
  span: number;
}

/** Collapses consecutive columns sharing a group into one colSpan cell;
 * ungrouped columns (and any run change) start a fresh cell. */
function buildGroupHeaderCells(
  columns: { key: string }[],
  columnGroups: { label: string; keys: string[] }[],
): GroupHeaderCell[] {
  const keyToLabel = new Map<string, string>();
  for (const group of columnGroups) {
    for (const key of group.keys) keyToLabel.set(key, group.label);
  }

  const cells: GroupHeaderCell[] = [];
  for (const column of columns) {
    const label = keyToLabel.get(column.key) ?? null;
    const last = cells[cells.length - 1];
    if (last && last.label === label) {
      last.span += 1;
    } else {
      cells.push({ label, span: 1 });
    }
  }
  return cells;
}

export function DataGrid({
  queryKey,
  adapter,
  readOnlyColumnKeys = [],
  isRowFlagged,
  flaggedLabel = "Flagged",
  selectOptions,
  rowActions,
  longTextColumnKeys = [],
  columnGroups,
  confirmDelete,
}: DataGridProps) {
  const [pendingDelete, setPendingDelete] = useState<SheetRow | null>(null);
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

  const updateCell = (rowId: number, key: string, value: string) =>
    runMutation(() => updateRow.mutateAsync({ rowId, data: { [key]: value } }), "Failed to update cell");

  const handleUpload = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    runMutation(() => uploadSheet.mutateAsync(files[0]), "Failed to upload sheet").then(() => {
      if (fileInputRef.current) fileInputRef.current.value = "";
    });
  };

  const groupHeaderCells = columnGroups ? buildGroupHeaderCells(sheet.columns, columnGroups) : null;

  return (
    <div className="data-grid">
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

      {/* A wide sheet scrolls in here rather than widening the whole page. */}
      <div className="table-scroll">
        <table>
          <thead>
            {groupHeaderCells && (
              <tr className="data-grid-group-row">
                {groupHeaderCells.map((cell, index) => (
                  <th key={index} colSpan={cell.span}>
                    {cell.label ?? ""}
                  </th>
                ))}
                <th />
              </tr>
            )}
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
                    const options = selectOptions?.[column.key];
                    const currentValue = cellText(row.data[column.key]);

                    if (isReadOnly) {
                      return (
                        <td
                          key={column.key}
                          data-column={column.key}
                          data-type={column.data_type}
                        >
                          <span>{currentValue}</span>
                        </td>
                      );
                    }

                    if (options) {
                      const knownValues = new Set(["", ...options.map((o) => o.value)]);
                      return (
                        <td
                          key={column.key}
                          data-column={column.key}
                          data-type={column.data_type}
                        >
                          <select
                            aria-label={`${column.label} for row ${row.id}`}
                            value={currentValue}
                            onChange={(e) => updateCell(row.id, column.key, e.target.value)}
                          >
                            <option value="">Unassigned</option>
                            {!knownValues.has(currentValue) && (
                              <option value={currentValue} disabled>
                                {currentValue} (unrecognized)
                              </option>
                            )}
                            {options.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </td>
                      );
                    }

                    const isLongText = longTextColumnKeys.includes(column.key);
                    return (
                      <td
                        key={column.key}
                        data-column={column.key}
                        data-type={column.data_type}
                        data-long-text={isLongText ? "true" : undefined}
                      >
                        {isLongText ? (
                          <textarea
                            aria-label={`${column.label} for row ${row.id}`}
                            defaultValue={currentValue}
                            rows={2}
                            onBlur={(e) => updateCell(row.id, column.key, e.target.value)}
                          />
                        ) : (
                          <input
                            aria-label={`${column.label} for row ${row.id}`}
                            defaultValue={currentValue}
                            onBlur={(e) => updateCell(row.id, column.key, e.target.value)}
                          />
                        )}
                      </td>
                    );
                  })}
                  <td>
                    {flagged && <span className="flag-chip">{flaggedLabel}</span>}
                    {rowActions?.(row)}
                    <button
                      onClick={() =>
                        confirmDelete ? setPendingDelete(row) : handleDeleteRow(row.id)
                      }
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              );
            })}
            <tr>
              {sheet.columns.map((column) => (
                <td key={column.key} data-column={column.key} data-type={column.data_type}>
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

      {pendingDelete && confirmDelete && (
        <ConfirmDialog
          title="Delete this row?"
          message={confirmDelete(pendingDelete)}
          isPending={deleteRow.isPending}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => {
            const rowId = pendingDelete.id;
            setPendingDelete(null);
            handleDeleteRow(rowId);
          }}
        />
      )}
    </div>
  );
}
