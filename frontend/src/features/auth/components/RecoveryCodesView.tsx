import { useState } from "react";

interface RecoveryCodesViewProps {
  codes: string[];
  /** Called when they confirm the codes are saved. */
  onDone: () => void | Promise<unknown>;
}

/** The recovery codes, shown once. They can't be got back, so the way out is a
 * checkbox: "Done" stays disabled until they say they have kept them. */
export function RecoveryCodesView({ codes, onDone }: RecoveryCodesViewProps) {
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  const text = codes.join("\n");

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([`${text}\n`], { type: "text/plain" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "recovery-codes.txt";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="recovery-codes">
      <h2>Save your recovery codes</h2>
      <p>
        If you lose your phone, each of these signs you in once. They are shown only now. Keep
        them somewhere safe, such as a password manager.
      </p>
      <ul aria-label="Recovery codes" className="recovery-code-list">
        {codes.map((code) => (
          <li key={code}>
            <code>{code}</code>
          </li>
        ))}
      </ul>
      <div className="recovery-code-actions">
        <button type="button" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
        <button type="button" onClick={download}>
          Download
        </button>
      </div>
      <label className="checkbox-row">
        <input type="checkbox" checked={saved} onChange={(e) => setSaved(e.target.checked)} />
        I have saved these codes
      </label>
      <button type="button" disabled={!saved} onClick={onDone}>
        Done
      </button>
    </div>
  );
}
