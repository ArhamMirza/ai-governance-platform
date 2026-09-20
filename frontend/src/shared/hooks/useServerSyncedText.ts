import { useState } from "react";

/**
 * Editable text that keeps up with the server until someone edits it.
 *
 * These fields copy the record into local state so typing stays responsive,
 * and save on blur when local differs from the server. Copied once and never
 * again, that goes wrong the moment the record changes underneath: applying
 * an AI draft, or a colleague's save. The field keeps showing the old text,
 * the next blur sees "local differs from server", and saves the old text
 * straight back over the new -- silently undoing what was just applied.
 *
 * So the local copy follows the server while it still matches what the
 * server last said. Once the person has edited it, their text wins and is
 * left alone; they are the one who decides what to save.
 */
export function useServerSyncedText(serverValue: string) {
  const [text, setText] = useState(serverValue);
  const [lastServerValue, setLastServerValue] = useState(serverValue);

  if (serverValue !== lastServerValue) {
    // Adjusting state during render is React's own pattern for following a
    // prop: it re-renders immediately, before anything is painted or saved.
    setLastServerValue(serverValue);
    if (text === lastServerValue) {
      setText(serverValue);
    }
  }

  return [text, setText] as const;
}
