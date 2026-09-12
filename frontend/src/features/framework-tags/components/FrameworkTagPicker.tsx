import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useFrameworkControls } from "../../framework-controls/hooks";
import type { FrameworkControl } from "../../framework-controls/types";
import { useFrameworkTags, useSetFrameworkTags } from "../hooks";

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

  const [isEditing, setIsEditing] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  if (tagsLoading || controlsLoading) return <p>Loading framework tags...</p>;
  if (tagsError || !tags || !controls) return <p>Failed to load framework tags.</p>;

  const startEditing = () => {
    setSelected(new Set(tags.map((tag) => tag.id)));
    setError(null);
    setIsEditing(true);
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
      {groupByFramework(controls).map(([framework, frameworkControls]) => (
        <fieldset key={framework} className="framework-tag-group">
          <legend>{FRAMEWORK_LABELS[framework] ?? framework}</legend>
          {frameworkControls.map((control) => {
            const inputId = `framework-tag-${control.id}`;
            return (
              <label key={control.id} htmlFor={inputId} className="framework-tag-option">
                <input
                  id={inputId}
                  type="checkbox"
                  checked={selected.has(control.id)}
                  onChange={() => toggle(control.id)}
                />
                <span>
                  <strong>{control.code}</strong> {control.title}
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
