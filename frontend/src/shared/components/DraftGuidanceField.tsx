import { useId, useState } from "react";

interface DraftGuidanceFieldProps {
  label: string;
  placeholder: string;
  submitLabel: string;
  pendingLabel: string;
  isPending: boolean;
  onSubmit: (instructions: string) => void;
}

/** A free-text instructions box beside a "Draft with AI" action -- guidance
 * layered on top of whatever the draft would otherwise gather on its own.
 * Used both to guide a first draft and, on a pending draft's review screen,
 * to revise it: same field, same submit action, generate called again. */
export function DraftGuidanceField({
  label,
  placeholder,
  submitLabel,
  pendingLabel,
  isPending,
  onSubmit,
}: DraftGuidanceFieldProps) {
  const [instructions, setInstructions] = useState("");
  const id = useId();

  return (
    <div className="draft-guidance-field">
      <label htmlFor={id}>{label}</label>
      <textarea
        id={id}
        rows={2}
        value={instructions}
        onChange={(e) => setInstructions(e.target.value)}
        placeholder={placeholder}
        disabled={isPending}
      />
      <button type="button" onClick={() => onSubmit(instructions.trim())} disabled={isPending}>
        {isPending ? pendingLabel : submitLabel}
      </button>
    </div>
  );
}
