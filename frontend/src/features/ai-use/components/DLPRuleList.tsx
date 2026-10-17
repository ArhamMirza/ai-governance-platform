import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { CLASSIFICATION_OPTIONS } from "../../ai-tools/labels";
import type { DataClassification } from "../../ai-tools/types";
import {
  useBuiltinDetectors,
  useDLPRules,
  useDeleteDLPRule,
  useUpdateDLPRule,
} from "../hooks";
import { ACTION_OPTIONS, KIND_LABELS, describeRule, splitKeywords } from "../labels";
import type { DLPAction, DLPRule, DLPRuleUpdateInput } from "../types";

/** One rule, with its day-to-day switches inline and the definition behind
 * "Edit". Changes save as they are made. */
function RuleRow({ rule, detectorLabel }: { rule: DLPRule; detectorLabel: (key: string) => string }) {
  const update = useUpdateDLPRule(rule.id);
  const remove = useDeleteDLPRule();
  const [editing, setEditing] = useState(false);

  const save = (data: DLPRuleUpdateInput) => update.mutate(data);
  const handleDelete = () => {
    if (window.confirm(`Delete the rule "${rule.name}"?`)) remove.mutate(rule.id);
  };

  return (
    <>
      <tr className={rule.enabled ? undefined : "row-muted"}>
        <td>
          <strong>{rule.name}</strong>
          {rule.description && <div className="approval-note">{rule.description}</div>}
        </td>
        <td>
          {KIND_LABELS[rule.kind]}
          <div className="approval-note">{describeRule(rule, detectorLabel)}</div>
        </td>
        <td>
          <select
            aria-label={`Data class for ${rule.name}`}
            value={rule.classification}
            onChange={(e) => save({ classification: e.target.value as DataClassification })}
          >
            {CLASSIFICATION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </td>
        <td>
          <select
            aria-label={`Action for ${rule.name}`}
            value={rule.action}
            onChange={(e) => save({ action: e.target.value as DLPAction })}
          >
            {ACTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </td>
        <td>
          <label>
            <input
              type="checkbox"
              aria-label={`Switch on ${rule.name}`}
              checked={rule.enabled}
              onChange={(e) => save({ enabled: e.target.checked })}
            />{" "}
            On
          </label>
        </td>
        <td>
          <button onClick={() => setEditing((open) => !open)}>{editing ? "Close" : "Edit"}</button>{" "}
          <button onClick={handleDelete} disabled={remove.isPending}>
            Delete
          </button>
        </td>
      </tr>
      {editing && (
        <tr>
          <td colSpan={6}>
            <RuleEditor rule={rule} onSave={save} />
            {update.isError && (
              <p role="alert">{readError(update.error, "Failed to save the rule.")}</p>
            )}
          </td>
        </tr>
      )}
      {remove.isError && (
        <tr>
          <td colSpan={6}>
            <p role="alert">{readError(remove.error, "Failed to delete the rule.")}</p>
          </td>
        </tr>
      )}
    </>
  );
}

function RuleEditor({ rule, onSave }: { rule: DLPRule; onSave: (data: DLPRuleUpdateInput) => void }) {
  const { data: detectors } = useBuiltinDetectors();

  return (
    <div>
      <div>
        <label htmlFor={`rule-name-${rule.id}`}>Rule</label>
        <input
          id={`rule-name-${rule.id}`}
          defaultValue={rule.name}
          onBlur={(e) => {
            const name = e.target.value.trim();
            if (name && name !== rule.name) onSave({ name });
          }}
        />
      </div>
      <div>
        <label htmlFor={`rule-description-${rule.id}`}>Why it exists</label>
        <textarea
          id={`rule-description-${rule.id}`}
          defaultValue={rule.description ?? ""}
          onBlur={(e) => {
            if (e.target.value !== (rule.description ?? "")) {
              onSave({ description: e.target.value.trim() || null });
            }
          }}
        />
      </div>
      {rule.kind === "builtin" && (
        <div>
          <label htmlFor={`rule-detector-${rule.id}`}>Detector</label>
          <select
            id={`rule-detector-${rule.id}`}
            value={rule.builtin_key ?? ""}
            onChange={(e) => onSave({ builtin_key: e.target.value })}
          >
            {(detectors ?? []).map((detector) => (
              <option key={detector.key} value={detector.key}>
                {detector.label}
              </option>
            ))}
          </select>
        </div>
      )}
      {rule.kind === "keywords" && (
        <div>
          <label htmlFor={`rule-keywords-${rule.id}`}>Words and phrases</label>
          <textarea
            id={`rule-keywords-${rule.id}`}
            defaultValue={(rule.keywords ?? []).join("\n")}
            onBlur={(e) => {
              const keywords = splitKeywords(e.target.value);
              if (keywords.join("\n") !== (rule.keywords ?? []).join("\n")) onSave({ keywords });
            }}
          />
        </div>
      )}
      {rule.kind === "regex" && (
        <div>
          <label htmlFor={`rule-pattern-${rule.id}`}>Pattern</label>
          <input
            id={`rule-pattern-${rule.id}`}
            defaultValue={rule.pattern ?? ""}
            onBlur={(e) => {
              if (e.target.value.trim() !== (rule.pattern ?? "")) {
                onSave({ pattern: e.target.value.trim() });
              }
            }}
          />
        </div>
      )}
    </div>
  );
}

/** Every rule the extension applies, with the switches that matter day to day. */
export function DLPRuleList() {
  const { data: rules, isLoading, isError } = useDLPRules();
  const { data: detectors } = useBuiltinDetectors();

  if (isLoading) return <p>Loading rules...</p>;
  if (isError) return <p>Failed to load rules.</p>;
  if (!rules || rules.length === 0) {
    return <p>No rules yet. Nothing is checked until you add one.</p>;
  }

  const detectorLabel = (key: string) =>
    detectors?.find((detector) => detector.key === key)?.label ?? key;

  return (
    <table>
      <thead>
        <tr>
          <th>Rule</th>
          <th>Looks for</th>
          <th>Data class</th>
          <th>When it matches</th>
          <th>Status</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {rules.map((rule) => (
          <RuleRow key={rule.id} rule={rule} detectorLabel={detectorLabel} />
        ))}
      </tbody>
    </table>
  );
}
