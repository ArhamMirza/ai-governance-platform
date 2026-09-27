import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { useManagementReviewSettings, useUpdateManagementReviewSettings } from "../hooks";

const SETTINGS_ENTITY_ID = 1;

export function ManagementReviewSettingsPanel() {
  const { data: settings, isLoading, isError } = useManagementReviewSettings();
  const updateSettings = useUpdateManagementReviewSettings();

  const [isEditing, setIsEditing] = useState(false);
  const [recurring, setRecurring] = useState(false);
  const [intervalMonths, setIntervalMonths] = useState("");
  const [startDate, setStartDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading management review settings...</p>;
  if (isError || !settings) return <p>Failed to load management review settings.</p>;

  const startEditing = () => {
    setRecurring(settings.interval_months !== null);
    setIntervalMonths(settings.interval_months ? String(settings.interval_months) : "");
    setStartDate(settings.start_date ?? "");
    setError(null);
    setIsEditing(true);
  };

  const handleSave = async () => {
    setError(null);
    try {
      await updateSettings.mutateAsync({
        interval_months: recurring ? Number(intervalMonths) : null,
        start_date: recurring ? startDate : null,
      });
      setIsEditing(false);
    } catch (err) {
      setError(readError(err, "Failed to save management review settings"));
    }
  };

  return (
    <section className="criteria-editor">
      <div className="criteria-editor-header">
        <div>
          <h3>Management Review Schedule</h3>
          <p>
            ISO/IEC 42001 Clause 9.3 -- top management reviews the AI management system at
            planned intervals. Configure a recurring interval, or leave reviews logged as they
            happen with no due date.
          </p>
        </div>
        <div className="criteria-editor-actions">
          {settings.overdue && <span className="flag-chip">Overdue</span>}
          {!isEditing && <button onClick={startEditing}>Edit</button>}
        </div>
      </div>

      {error && <p role="alert">{error}</p>}

      {isEditing ? (
        <div className="criteria-editor-form">
          <label>
            <input
              type="checkbox"
              checked={recurring}
              onChange={(e) => setRecurring(e.target.checked)}
            />
            Recurring reviews
          </label>
          {recurring && (
            <>
              <div>
                <label htmlFor="management-review-interval">Every how many months</label>
                <input
                  id="management-review-interval"
                  type="number"
                  min={1}
                  value={intervalMonths}
                  onChange={(e) => setIntervalMonths(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="management-review-start-date">First review due</label>
                <input
                  id="management-review-start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
            </>
          )}
          <div className="criteria-editor-buttons">
            <button onClick={handleSave} disabled={updateSettings.isPending}>
              {updateSettings.isPending ? "Saving..." : "Save"}
            </button>
            <button onClick={() => setIsEditing(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <p>
          {settings.interval_months
            ? `Every ${settings.interval_months} month(s). Next due ${settings.next_due_date ?? "—"}.`
            : "No schedule configured -- reviews are logged as they happen."}
        </p>
      )}

      <h4>Framework Tags</h4>
      <FrameworkTagPicker entityType="ManagementReviewSettings" entityId={SETTINGS_ENTITY_ID} />
    </section>
  );
}
