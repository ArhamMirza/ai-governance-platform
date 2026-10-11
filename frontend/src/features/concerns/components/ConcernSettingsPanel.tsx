import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useServerSyncedText } from "../../../shared/hooks/useServerSyncedText";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { useConcernSettings, useUpdateConcernSettings } from "../hooks";
import type { ConcernSettings } from "../types";

function ProcessDescription({ settings }: { settings: ConcernSettings }) {
  const update = useUpdateConcernSettings();
  const [text, setText] = useServerSyncedText(settings.process_description ?? "");

  return (
    <div>
      <label htmlFor="concern-process">What staff are told about reporting</label>
      <textarea
        id="concern-process"
        rows={5}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() =>
          text !== (settings.process_description ?? "") &&
          update.mutate({ process_description: text || null })
        }
        placeholder="How to raise a concern, what happens next, and who to ask."
      />
      {update.isError && <p role="alert">{readError(update.error, "Failed to save.")}</p>}
    </div>
  );
}

function AcknowledgeWithin({ settings }: { settings: ConcernSettings }) {
  const update = useUpdateConcernSettings();
  const [days, setDays] = useState(String(settings.acknowledge_within_days));
  const valid = /^\d+$/.test(days) && Number(days) >= 1 && Number(days) <= 90;

  return (
    <div>
      <label htmlFor="concern-ack-days">Acknowledge within (days)</label>
      <input
        id="concern-ack-days"
        type="number"
        min={1}
        max={90}
        value={days}
        onChange={(e) => setDays(e.target.value)}
      />
      <button
        onClick={() => update.mutate({ acknowledge_within_days: Number(days) })}
        disabled={!valid || Number(days) === settings.acknowledge_within_days || update.isPending}
      >
        Save
      </button>
      {!valid && <p className="approval-note">Choose a whole number of days from 1 to 90.</p>}
      {update.isError && <p role="alert">{readError(update.error, "Failed to save.")}</p>}
    </div>
  );
}

/** How reporting works: what staff are told, how quickly a concern must be
 * acknowledged, and the clauses this process evidences (A.3.3). */
export function ConcernSettingsPanel() {
  const { data: settings, isLoading, isError } = useConcernSettings();

  if (isLoading) return <p>Loading settings...</p>;
  if (isError || !settings) return <p>Failed to load settings.</p>;

  return (
    <section>
      <h2>How reporting works</h2>
      <ProcessDescription settings={settings} />
      <AcknowledgeWithin settings={settings} />
      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="ConcernSettings" entityId={settings.id} />
    </section>
  );
}
