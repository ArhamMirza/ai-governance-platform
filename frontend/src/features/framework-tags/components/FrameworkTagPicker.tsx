import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useFrameworkControls } from "../../framework-controls/hooks";
import type { FrameworkControl } from "../../framework-controls/types";
import { useFrameworkTags, useSetFrameworkTags, useSuggestFrameworkTags } from "../hooks";

interface FrameworkTagPickerProps {
  entityType: string;
  entityId: number;
  /** Other query keys to invalidate on save -- e.g. the parent entity's own
   * detail query, when it embeds tags in its read response. */
  extraInvalidateKeys?: readonly (readonly unknown[])[];
}

const FRAMEWORK_LABELS: Record<string, string> = {
  iso_42001: "ISO 42001",
  eu_ai_act: "EU AI Act",
};

function groupByFramework(controls: FrameworkControl[]): [string, FrameworkControl[]][] {
  const groups = new Map<string, FrameworkControl[]>();
  for (const control of controls) {
    const group = groups.get(control.framework) ?? [];
    group.push(control);
    groups.set(control.framework, group);
  }
  return [...groups.entries()];
}

export function FrameworkTagPicker({
  entityType,
  entityId,
  extraInvalidateKeys = [],
}: FrameworkTagPickerProps) {
  const { data: tags, isLoading: tagsLoading, isError: tagsError } = useFrameworkTags(
    entityType,
    entityId,
  );
  const { data: controls, isLoading: controlsLoading } = useFrameworkControls();
  const setTags = useSetFrameworkTags(entityType, entityId, extraInvalidateKeys);
  const suggestTags = useSuggestFrameworkTags(entityType, entityId);

  const [isEditing, setIsEditing] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  // Controls the last "Suggest Tags" click added, so they can be highlighted
  // distinctly from ones already picked by hand -- cleared whenever editing
  // starts or stops, never persisted.
  const [suggested, setSuggested] = useState<Set<number>>(new Set());
  // Tracked locally rather than read from suggestTags.isSuccess/data: this
  // needs to say "a suggestion request just came back empty," not "the
  // last-ever mutation result was empty," which is a different question
  // once Suggest Tags has been clicked more than once.
  const [hasSuggested, setHasSuggested] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (tagsLoading || controlsLoading) return <p>Loading framework tags...</p>;
  if (tagsError || !tags || !controls) return <p>Failed to load framework tags.</p>;

  const startEditing = () => {
    setSelected(new Set(tags.map((tag) => tag.id)));
    setSuggested(new Set());
    setHasSuggested(false);
    setError(null);
    setIsEditing(true);
  };

  const handleSuggest = async () => {
    setError(null);
    try {
      const results = await suggestTags.mutateAsync();
      setSuggested(new Set(results.map((control) => control.id)));
      setHasSuggested(true);
      // Layers onto whatever is already picked -- a suggestion never
      // unchecks something a person already chose by hand.
      setSelected((prev) => new Set([...prev, ...results.map((control) => control.id)]));
    } catch (err) {
      setError(readError(err, "Failed to suggest framework tags"));
    }
  };

  const toggle = (controlId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(controlId)) next.delete(controlId);
      else next.add(controlId);
      return next;
    });
  };

  const handleSave = async () => {
    setError(null);
    try {
      await setTags.mutateAsync([...selected]);
      setIsEditing(false);
    } catch (err) {
      setError(readError(err, "Failed to save framework tags"));
    }
  };

  if (!isEditing) {
    return (
      <div className="framework-tag-picker">
        <div className="framework-tag-chips">
          {tags.length === 0 ? (
            <span className="framework-tags-empty">No framework tags yet.</span>
          ) : (
            tags.map((tag) => (
              <span key={tag.id} className="framework-tag-chip" title={tag.title}>
                {FRAMEWORK_LABELS[tag.framework] ?? tag.framework}:{tag.code}
              </span>
            ))
          )}
        </div>
        <button onClick={startEditing}>Edit Tags</button>
      </div>
    );
  }

  return (
    <div className="framework-tag-picker is-editing">
      {error && <p role="alert">{error}</p>}
      <div className="framework-tag-picker-actions">
        <button type="button" onClick={handleSuggest} disabled={suggestTags.isPending}>
          {suggestTags.isPending ? "Suggesting..." : "Suggest Tags"}
        </button>
      </div>
      {hasSuggested && suggested.size === 0 && (
        <p className="framework-tags-empty">
          Nothing in this record's text resembled a control closely enough to suggest.
        </p>
      )}
      {groupByFramework(controls).map(([framework, frameworkControls]) => (
        <fieldset key={framework} className="framework-tag-group">
          <legend>{FRAMEWORK_LABELS[framework] ?? framework}</legend>
          {frameworkControls.map((control) => {
            const inputId = `framework-tag-${control.id}`;
            return (
              <label
                key={control.id}
                htmlFor={inputId}
                className="framework-tag-option"
                data-suggested={suggested.has(control.id) || undefined}
              >
                <input
                  id={inputId}
                  type="checkbox"
                  checked={selected.has(control.id)}
                  onChange={() => toggle(control.id)}
                />
                <span>
                  <strong>{control.code}</strong> {control.title}
                  {suggested.has(control.id) && (
                    <span className="framework-tag-suggested-label">Suggested</span>
                  )}
                </span>
              </label>
            );
          })}
        </fieldset>
      ))}
      <div className="framework-tag-picker-actions">
        <button type="submit" onClick={handleSave} disabled={setTags.isPending}>
          {setTags.isPending ? "Saving..." : "Save"}
        </button>
        <button onClick={() => setIsEditing(false)}>Cancel</button>
      </div>
    </div>
  );
}
