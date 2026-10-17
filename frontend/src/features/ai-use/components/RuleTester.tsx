import { useMemo, useState } from "react";

import { CLASSIFICATION_OPTIONS } from "../../ai-tools/labels";
import { type Classification, mask, scan } from "../../../shared/dlp/detectors";
import { useDLPRules } from "../hooks";
import { actionLabel } from "../labels";

/** Paste some text and see which rules would act on it, and how, for a tool
 * cleared for a given class of data. Runs the same code the browser extension
 * runs (shared/dlp/detectors), entirely on this page: nothing typed here is
 * sent anywhere. */
export function RuleTester() {
  const { data: rules } = useDLPRules();
  const [text, setText] = useState("");
  const [clearance, setClearance] = useState<"none" | Classification>("none");

  const enabled = useMemo(() => (rules ?? []).filter((rule) => rule.enabled), [rules]);
  const hits = useMemo(
    () => scan(text, enabled, clearance === "none" ? null : clearance),
    [text, enabled, clearance],
  );

  return (
    <section>
      <h3>Try your rules</h3>
      <p className="approval-note">
        This runs in your browser. What you type here is not sent to the server or stored.
      </p>
      <div>
        <label htmlFor="tester-clearance">Tool the text is going into</label>
        <select
          id="tester-clearance"
          value={clearance}
          onChange={(e) => setClearance(e.target.value as "none" | Classification)}
        >
          <option value="none">One that isn't approved</option>
          {CLASSIFICATION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              Approved up to {option.label.toLowerCase()} data
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="tester-text">Text to check</label>
        <textarea id="tester-text" value={text} onChange={(e) => setText(e.target.value)} />
      </div>
      {text.trim() === "" ? null : hits.length === 0 ? (
        <p role="status">Nothing in this text would be stopped or flagged.</p>
      ) : (
        <ul className="plain-list" aria-label="Rules that matched">
          {hits.map((hit) => (
            <li key={hit.rule.id} className="reporter-concern">
              <p>
                <strong>{hit.rule.name}</strong> -- {actionLabel(hit.rule.action).toLowerCase()}
              </p>
              <p className="approval-note">
                Found {hit.ranges.length} time{hit.ranges.length === 1 ? "" : "s"}:{" "}
                {hit.ranges.map((range) => mask(text.slice(range.start, range.end))).join(", ")}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
