import { useState } from "react";
import { Link } from "react-router-dom";

import type { ConcernSubmitted } from "../types";

/** Shown once after sending. The tracking code is the only way back to an
 * anonymous concern and only its hash is kept, so this is the one chance to
 * copy it. */
export function ConcernSubmittedNotice({ result }: { result: ConcernSubmitted }) {
  const [copied, setCopied] = useState(false);
  const anonymous = result.concern.is_anonymous;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(result.tracking_code);
      setCopied(true);
    } catch {
      // No clipboard access: the code is on screen to copy by hand.
    }
  };

  return (
    <section role="status">
      <h2>Thank you -- your concern has been received</h2>
      <p>
        {anonymous
          ? "It was sent anonymously. Nothing that identifies you was stored with it."
          : "It was sent under your name."}
      </p>
      <p>Your tracking code:</p>
      <p className="tracking-code">{result.tracking_code}</p>
      <button type="button" onClick={copy}>
        {copied ? "Copied" : "Copy code"}
      </button>
      <p className="approval-note">
        {anonymous
          ? "Keep this code: it's the only way to check on your concern, and it can't be shown again. Look it up under My concerns."
          : "You'll find this concern under My concerns. The code works there too."}
      </p>
      <p>
        <Link to="/concerns">Go to My concerns</Link> · <Link to="/">Back home</Link>
      </p>
    </section>
  );
}
