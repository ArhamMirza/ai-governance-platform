import { useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import type { TaggedItem } from "../../framework-mapping/types";
import { useFrameworkSoa, useUpdateFrameworkSoaEntry } from "../hooks";
import type { FrameworkSoaEntry } from "../types";

function TaggedItemChips({ items }: { items: TaggedItem[] }) {
  if (items.length === 0) {
    return <span className="framework-tags-empty">Not tagged to anything yet.</span>;
  }
  return (
    <div className="framework-tag-chips">
      {items.map((item) => (
        <span key={`${item.entity_type}-${item.entity_id}`} className="framework-tag-chip">
          {item.entity_type}: {item.label}
        </span>
      ))}
    </div>
  );
}

function SoaRow({ entry }: { entry: FrameworkSoaEntry }) {
  const updateEntry = useUpdateFrameworkSoaEntry();
  const [justification, setJustification] = useState(entry.justification ?? "");
  const [error, setError] = useState<string | null>(null);

  const handleApplicabilityChange = async (applicability: string) => {
    setError(null);
    try {
      await updateEntry.mutateAsync({
        controlId: entry.id,
        data: { applicability, justification: justification || null },
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update applicability");
    }
  };

  const handleJustificationBlur = async () => {
    if (justification === (entry.justification ?? "")) return;
    setError(null);
    try {
      await updateEntry.mutateAsync({
        controlId: entry.id,
        data: { applicability: entry.applicability, justification: justification || null },
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update justification");
    }
  };

  return (
    <tr>
      <td>{entry.code}</td>
      <td>{entry.title}</td>
      <td data-column="applicability" data-type="text">
        <select
          aria-label={`Applicability for ${entry.code}`}
          value={entry.applicability}
          onChange={(e) => handleApplicabilityChange(e.target.value)}
        >
          <option value="applicable">Applicable</option>
          <option value="not_applicable">Not Applicable</option>
        </select>
      </td>
      <td data-column="justification" data-type="text" data-long-text="true">
        <textarea
          aria-label={`Justification for ${entry.code}`}
          value={justification}
          rows={2}
          onChange={(e) => setJustification(e.target.value)}
          onBlur={handleJustificationBlur}
        />
        {error && <p role="alert">{error}</p>}
      </td>
      <td>
        <TaggedItemChips items={entry.tagged_items} />
      </td>
    </tr>
  );
}

export function SoaTable() {
  const { data: entries, isLoading, isError } = useFrameworkSoa();

  if (isLoading) return <p>Loading statement of applicability...</p>;
  if (isError || !entries) return <p>Failed to load statement of applicability.</p>;

  return (
    <div className="data-grid">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Title</th>
              <th>Applicability</th>
              <th>Justification</th>
              <th>Tagged Items</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <SoaRow key={entry.id} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
