import { useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { useResetRiskCriteria, useRiskCriteria, useUpdateRiskCriteria } from "../hooks";

/** The API returns FastAPI's {"detail": "..."} envelope as raw text. */
function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}

export function RiskCriteriaEditor() {
  const { data: criteria, isLoading, isError } = useRiskCriteria();
  const updateCriteria = useUpdateRiskCriteria();
  const resetCriteria = useResetRiskCriteria();

  const [isEditing, setIsEditing] = useState(false);
  const [mediumMin, setMediumMin] = useState("");
  const [highMin, setHighMin] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading risk criteria...</p>;
  if (isError || !criteria) return <p>Failed to load risk criteria.</p>;

  const startEditing = () => {
    setMediumMin(String(criteria.medium_min_score));
    setHighMin(String(criteria.high_min_score));
    setError(null);
    setIsEditing(true);
  };

  const handleSave = async () => {
    setError(null);
    try {
      await updateCriteria.mutateAsync({
        medium_min_score: Number(mediumMin),
        high_min_score: Number(highMin),
      });
      setIsEditing(false);
    } catch (err) {
      setError(readError(err, "Failed to save risk criteria"));
    }
  };

  const handleReset = async () => {
    setError(null);
    try {
      await resetCriteria.mutateAsync();
      setIsEditing(false);
    } catch (err) {
      setError(readError(err, "Failed to reset risk criteria"));
    }
  };

  const bandRows = [
    {
      key: "low",
      label: "Low",
      range: `${criteria.min_score} – ${criteria.medium_min_score - 1}`,
    },
    {
      key: "medium",
      label: "Medium",
      range: `${criteria.medium_min_score} – ${criteria.high_min_score - 1}`,
    },
    {
      key: "high",
      label: "High",
      range: `${criteria.high_min_score} – ${criteria.max_score}`,
    },
  ];

  return (
    <section className="criteria-editor">
      <div className="criteria-editor-header">
        <div>
          <h3>Risk Criteria</h3>
          <p>
            Scores are likelihood × impact ({criteria.min_score}–{criteria.max_score}). These
            bands drive every severity count, the matrix shading, and the high-risk flag.
          </p>
        </div>
        <div className="criteria-editor-actions">
          {criteria.is_default && <span className="criteria-default-badge">Using defaults</span>}
          {!isEditing && (
            <button onClick={startEditing}>Edit</button>
          )}
        </div>
      </div>

      {error && <p role="alert">{error}</p>}

      {isEditing ? (
        <div className="criteria-editor-form">
          <div>
            <label htmlFor="criteria-medium-min">Medium band starts at</label>
            <input
              id="criteria-medium-min"
              type="number"
              min={criteria.min_score + 1}
              max={criteria.max_score}
              value={mediumMin}
              onChange={(e) => setMediumMin(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="criteria-high-min">High band starts at</label>
            <input
              id="criteria-high-min"
              type="number"
              min={criteria.min_score + 1}
              max={criteria.max_score}
              value={highMin}
              onChange={(e) => setHighMin(e.target.value)}
            />
          </div>
          <div className="criteria-editor-buttons">
            <button type="submit" onClick={handleSave} disabled={updateCriteria.isPending}>
              {updateCriteria.isPending ? "Saving..." : "Save"}
            </button>
            <button onClick={() => setIsEditing(false)}>Cancel</button>
            <button onClick={handleReset} disabled={resetCriteria.isPending}>
              Restore defaults
            </button>
          </div>
        </div>
      ) : (
        <ul className="criteria-bands">
          {bandRows.map((band) => (
            <li key={band.key}>
              <span className="legend-dot" data-tone={band.key} />
              <span className="legend-label">{band.label}</span>
              <span className="legend-value">{band.range}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
