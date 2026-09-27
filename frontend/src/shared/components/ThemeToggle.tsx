import { useEffect, useState } from "react";

import { applyTheme, readStoredTheme, storeTheme, type ThemePreference } from "../theme";

const OPTIONS: { value: ThemePreference; label: string; title: string }[] = [
  { value: "system", label: "Auto", title: "Follow the operating system" },
  { value: "light", label: "Light", title: "Always light" },
  { value: "dark", label: "Dark", title: "Always dark" },
];

/**
 * Light / dark / follow-the-OS.
 *
 * "Auto" is the default and a real option rather than an implicit starting
 * state: someone whose machine switches at dusk should be able to keep that,
 * and someone who wants one theme regardless should be able to pin it.
 */
export function ThemeToggle() {
  const [preference, setPreference] = useState<ThemePreference>(() => readStoredTheme());

  // The inline script in index.html applies the stored preference before the
  // first paint; this keeps the element in step with later changes.
  useEffect(() => {
    applyTheme(preference);
  }, [preference]);

  const choose = (next: ThemePreference) => {
    setPreference(next);
    storeTheme(next);
  };

  return (
    <div className="theme-toggle" role="group" aria-label="Colour theme">
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          title={option.title}
          aria-pressed={preference === option.value}
          className={preference === option.value ? "active" : undefined}
          onClick={() => choose(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
