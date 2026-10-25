import { useState } from "react";
import { Link } from "react-router-dom";

import { useCurrentUser } from "../../auth/hooks";
import { hasPermission } from "../../auth/permissions";
import { useGettingStarted } from "../hooks";

const HIDDEN_KEY = "getting-started-hidden";

/** A convenience, not state anyone depends on: where storage is blocked or
 * empty the panel simply stays visible. */
function readHidden(): boolean {
  try {
    return window.localStorage.getItem(HIDDEN_KEY) === "1";
  } catch {
    return false;
  }
}

function writeHidden(hidden: boolean) {
  try {
    if (hidden) window.localStorage.setItem(HIDDEN_KEY, "1");
    else window.localStorage.removeItem(HIDDEN_KEY);
  } catch {
    // Nothing to do: it just won't be remembered.
  }
}

/**
 * What a new installation still needs, in the order to do it. Worked out by the
 * server from the records, so a step is ticked only when the work exists. Gone
 * for good once every required step is done; until then it can be hidden for
 * now, and brought back.
 */
export function GettingStartedPanel() {
  const { data: me } = useCurrentUser();
  // Only people who can make the records need to be told to.
  const canAct = hasPermission(me?.role, "edit");
  const { data } = useGettingStarted(canAct);
  const [hidden, setHidden] = useState(readHidden);

  if (!canAct || !data || data.complete) return null;

  const hide = (value: boolean) => {
    setHidden(value);
    writeHidden(value);
  };

  if (hidden) {
    return (
      <p className="getting-started-collapsed">
        <button
          type="button"
          className="link-button"
          onClick={() => hide(false)}
        >
          Show getting started
        </button>{" "}
        ({data.done_count} of {data.total} done)
      </p>
    );
  }

  const percent = Math.round((data.done_count / data.total) * 100);

  return (
    <section
      className="getting-started"
      aria-labelledby="getting-started-heading"
    >
      <div className="getting-started-head">
        <h2 id="getting-started-heading">Getting started</h2>
        <span className="getting-started-count">
          {data.done_count} of {data.total} done
        </span>
        <button type="button" onClick={() => hide(true)}>
          Hide for now
        </button>
      </div>
      <div
        className="usage-bar"
        role="progressbar"
        aria-label="Setup progress"
        aria-valuemin={0}
        aria-valuemax={data.total}
        aria-valuenow={data.done_count}
      >
        <span className="usage-bar-fill" style={{ width: `${percent}%` }} />
      </div>
      <ol className="getting-started-steps">
        {data.steps.map((step, index) => (
          <li
            key={step.key}
            data-done={step.done}
            data-next={step.key === data.next_key}
          >
            <span className="getting-started-mark" aria-hidden="true">
              {step.done ? "✓" : index + 1}
            </span>
            <div>
              <p className="getting-started-title">
                <span className="visually-hidden">
                  {step.done ? "Done: " : "To do: "}
                </span>
                <Link to={step.href}>{step.title}</Link>
                {step.optional && (
                  <span className="approval-note"> Optional</span>
                )}
                {step.key === data.next_key && (
                  <span className="getting-started-next"> Start here</span>
                )}
              </p>
              {!step.done && <p className="approval-note">{step.why}</p>}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
