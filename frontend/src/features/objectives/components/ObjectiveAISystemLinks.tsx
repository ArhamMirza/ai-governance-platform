import { useState } from "react";
import { Link } from "react-router-dom";

import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { aiSystemName } from "../../suppliers/labels";
import { useSetObjectiveAISystems } from "../hooks";
import type { ObjectiveDetail } from "../types";

/** The AI systems an objective measures or concerns -- each one's page
 * lists the objective back. */
export function ObjectiveAISystemLinks({ objective }: { objective: ObjectiveDetail }) {
  const { data: inventory } = useAISystemInventoryRows();
  const setLinks = useSetObjectiveAISystems(objective.id);
  const [adding, setAdding] = useState("");
  const rows = inventory?.rows ?? [];
  const nameOf = (rowId: number) => aiSystemName(rows.find((row) => row.id === rowId), rowId);
  const unlinked = rows.filter((row) => !objective.ai_system_row_ids.includes(row.id));

  return (
    <section>
      <h3>AI Systems</h3>
      {objective.ai_system_row_ids.length === 0 ? (
        <p>Not linked to any AI system.</p>
      ) : (
        <ul className="assessment-links">
          {objective.ai_system_row_ids.map((rowId) => {
            const name = nameOf(rowId);
            return (
              <li key={rowId}>
                <Link to={`/ai-systems/${rowId}`}>{name}</Link>{" "}
                <button
                  aria-label={`Remove ${name}`}
                  disabled={setLinks.isPending}
                  onClick={() =>
                    setLinks.mutate(objective.ai_system_row_ids.filter((id) => id !== rowId))
                  }
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
          <label htmlFor="objective-add-ai-system">Add AI system</label>
          <select
            id="objective-add-ai-system"
            value={adding}
            onChange={(e) => setAdding(e.target.value)}
          >
            <option value="">Choose an AI system</option>
            {unlinked.map((row) => (
              <option key={row.id} value={row.id}>
                {aiSystemName(row, row.id)}
              </option>
            ))}
          </select>
          <button
            disabled={!adding || setLinks.isPending}
            onClick={async () => {
              await setLinks.mutateAsync([...objective.ai_system_row_ids, Number(adding)]);
              setAdding("");
            }}
          >
            Link
          </button>
        </div>
      )}
    </section>
  );
}
