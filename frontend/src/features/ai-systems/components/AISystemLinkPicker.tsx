import { useState } from "react";
import { Link } from "react-router-dom";

import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { aiSystemName } from "../../suppliers/labels";

interface AISystemLinkPickerProps {
  /** Inventory row ids currently linked. */
  value: number[];
  /** Called with the full new set, so the caller saves it in one request. */
  onChange: (rowIds: number[]) => void;
  pending: boolean;
  /** Prefix for element ids, so two pickers on one page don't clash. */
  idPrefix: string;
  /** Shown when nothing is linked. */
  emptyText?: string;
}

/** The AI systems a record is linked to, each with a link to its page and
 * a Remove button, plus a select to add another. Used wherever a record
 * (an objective, a change ...) concerns particular AI systems. */
export function AISystemLinkPicker({
  value,
  onChange,
  pending,
  idPrefix,
  emptyText = "Not linked to any AI system.",
}: AISystemLinkPickerProps) {
  const { data: inventory } = useAISystemInventoryRows();
  const [adding, setAdding] = useState("");
  const rows = inventory?.rows ?? [];
  const nameOf = (rowId: number) => aiSystemName(rows.find((row) => row.id === rowId), rowId);
  const unlinked = rows.filter((row) => !value.includes(row.id));

  return (
    <>
      {value.length === 0 ? (
        <p>{emptyText}</p>
      ) : (
        <ul className="assessment-links">
          {value.map((rowId) => {
            const name = nameOf(rowId);
            return (
              <li key={rowId}>
                <Link to={`/ai-systems/${rowId}`}>{name}</Link>{" "}
                <button
                  aria-label={`Remove ${name}`}
                  disabled={pending}
                  onClick={() => onChange(value.filter((id) => id !== rowId))}
                >
                  Remove
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {unlinked.length > 0 && (
        <div className="inline-form">
          <label htmlFor={`${idPrefix}-add`}>Add AI system</label>
          <select id={`${idPrefix}-add`} value={adding} onChange={(e) => setAdding(e.target.value)}>
            <option value="">Choose an AI system</option>
            {unlinked.map((row) => (
              <option key={row.id} value={row.id}>
                {aiSystemName(row, row.id)}
              </option>
            ))}
          </select>
          <button
            disabled={!adding || pending}
            onClick={() => {
              onChange([...value, Number(adding)]);
              setAdding("");
            }}
          >
            Link
          </button>
        </div>
      )}
    </>
  );
}
