import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useAIUseSettings, useRotateEnrollmentKey, useUpdateAIUseSettings } from "../hooks";
import { ACTION_OPTIONS } from "../labels";
import type { DLPAction, EnrollmentKeyIssued } from "../types";

/** The key, once. It is held in this component's state only, so leaving the
 * page loses it for good -- as the server has only its hash. */
function IssuedKey({ issued }: { issued: EnrollmentKeyIssued }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(issued.key);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div role="status" className="reporter-concern">
      <p>
        <strong>Copy this key now.</strong> It is shown once and can't be shown again; the server
        keeps only a fingerprint of it. Put it in the extension's managed settings.
      </p>
      <code className="tracking-code">{issued.key}</code>
      <p>
        <button onClick={copy}>{copied ? "Copied" : "Copy key"}</button>
      </p>
    </div>
  );
}

export function AIUseSettingsPanel() {
  const { data: settings, isLoading, isError } = useAIUseSettings();
  const update = useUpdateAIUseSettings();
  const rotate = useRotateEnrollmentKey();
  const [issued, setIssued] = useState<EnrollmentKeyIssued | null>(null);
  const [days, setDays] = useState<string | null>(null);

  if (isLoading) return <p>Loading settings...</p>;
  if (isError || !settings) return <p>Failed to load settings.</p>;

  const retention = days ?? String(settings.retention_days);
  const retentionValue = Number(retention);
  const retentionValid = Number.isInteger(retentionValue) && retentionValue >= 7 && retentionValue <= 730;

  const makeKey = () => {
    if (
      settings.enrollment_key_issued &&
      !window.confirm(
        "This replaces the current key. Browsers using the old key stop reporting until you give them the new one. Continue?",
      )
    ) {
      return;
    }
    rotate.mutate(undefined, { onSuccess: setIssued });
  };

  return (
    <>
      <section>
        <h3>On an unapproved AI site</h3>
        <div>
          <label htmlFor="unapproved-action">What the browser does</label>
          <select
            id="unapproved-action"
            value={settings.unapproved_site_action}
            onChange={(e) => update.mutate({ unapproved_site_action: e.target.value as DLPAction })}
          >
            {ACTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label} -- {option.hint}
              </option>
            ))}
          </select>
        </div>
      </section>

      <section>
        <h3>What staff are told</h3>
        <div>
          <label htmlFor="staff-notice">Notice shown to employees</label>
          <textarea
            id="staff-notice"
            defaultValue={settings.staff_notice ?? ""}
            onBlur={(e) => {
              if (e.target.value !== (settings.staff_notice ?? "")) {
                update.mutate({ staff_notice: e.target.value.trim() || null });
              }
            }}
          />
          <p className="approval-note">
            Say what is monitored, what isn't, and how long it is kept. Staff read this on their AI
            tools page. Monitoring staff without telling them is unlawful in many places.
          </p>
        </div>
      </section>

      <section>
        <h3>How long counts are kept</h3>
        <div>
          <label htmlFor="retention-days">Days</label>
          <input
            id="retention-days"
            type="number"
            min={7}
            max={730}
            value={retention}
            onChange={(e) => setDays(e.target.value)}
          />
          {!retentionValid && <p role="alert">Keep them for a whole number of days from 7 to 730.</p>}
        </div>
        <button
          onClick={() => update.mutate({ retention_days: retentionValue }, { onSuccess: () => setDays(null) })}
          disabled={!retentionValid || update.isPending || retentionValue === settings.retention_days}
        >
          Save
        </button>
      </section>

      {update.isError && (
        <p role="alert">{readError(update.error, "Failed to save the setting.")}</p>
      )}

      <section>
        <h3>Browser extension key</h3>
        <p>
          {settings.enrollment_key_issued
            ? `A key ending ${settings.enrollment_key_hint} was made on ${settings.enrollment_key_created_on}.`
            : "No key has been made, so no browser can read the policy or report yet."}
        </p>
        <button onClick={makeKey} disabled={rotate.isPending}>
          {settings.enrollment_key_issued ? "Replace Key" : "Create Key"}
        </button>
        {rotate.isError && (
          <p role="alert">{readError(rotate.error, "Failed to make a key.")}</p>
        )}
        {issued && <IssuedKey issued={issued} />}
      </section>
    </>
  );
}
