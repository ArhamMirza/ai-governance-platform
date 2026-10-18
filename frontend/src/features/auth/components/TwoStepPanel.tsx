import { useState } from "react";

import {
  useDisableTwoStep,
  useNewRecoveryCodes,
  useTwoStepStatus,
} from "../hooks";
import { RecoveryCodesView } from "./RecoveryCodesView";
import { TwoStepProofForm } from "./TwoStepProofForm";
import { TwoStepSetup } from "./TwoStepSetup";

type Mode = "idle" | "setup" | "turning-off" | "new-codes";

/** Your own two-step sign-in, on the account page: turn it on, see how many
 * recovery codes are left, replace them, or turn it off. */
export function TwoStepPanel() {
  const { data: status, isLoading, isError } = useTwoStepStatus();
  const disable = useDisableTwoStep();
  const newCodes = useNewRecoveryCodes();
  const [mode, setMode] = useState<Mode>("idle");
  const [freshCodes, setFreshCodes] = useState<string[] | null>(null);

  if (isLoading) return <p>Loading...</p>;
  if (isError || !status) return <p role="alert">Couldn't load your two-step sign-in settings.</p>;

  const back = () => {
    disable.reset();
    newCodes.reset();
    setMode("idle");
  };

  if (freshCodes) {
    return (
      <section aria-label="Two-step sign-in">
        <RecoveryCodesView
          codes={freshCodes}
          onDone={() => {
            setFreshCodes(null);
            setMode("idle");
          }}
        />
      </section>
    );
  }

  return (
    <section aria-label="Two-step sign-in">
      <h2>Two-step sign-in</h2>

      {mode !== "setup" && !status.enabled && (
        <>
          <p>
            <span className="status-badge" data-status="retired">
              Off
            </span>{" "}
            Signing in needs only your password. Two-step sign-in adds a code from your phone, so
            a stolen password isn't enough.
          </p>
          <button type="button" onClick={() => setMode("setup")}>
            Set up two-step sign-in
          </button>
        </>
      )}

      {mode === "setup" && <TwoStepSetup onDone={back} onCancel={back} />}

      {status.enabled && mode === "idle" && (
        <>
          <p>
            <span className="status-badge" data-status="approved">
              On
            </span>{" "}
            Signing in needs your password and a code from your authenticator app.
          </p>
          <p className={status.recovery_codes_remaining <= 3 ? "text-warning" : undefined}>
            {status.recovery_codes_remaining} recovery code
            {status.recovery_codes_remaining === 1 ? "" : "s"} left
            {status.recovery_codes_remaining <= 3 ? ". Make new ones before you run out." : "."}
          </p>
          <button type="button" onClick={() => setMode("new-codes")}>
            Make new recovery codes
          </button>
          <button type="button" onClick={() => setMode("turning-off")}>
            Turn off
          </button>
        </>
      )}

      {status.enabled && mode === "new-codes" && (
        <TwoStepProofForm
          description="This replaces all your recovery codes; the old ones stop working."
          submitLabel="Make new codes"
          pendingLabel="Making..."
          isPending={newCodes.isPending}
          error={newCodes.error}
          onSubmit={async (proof) => {
            const result = await newCodes.mutateAsync(proof);
            setFreshCodes(result.recovery_codes);
          }}
          onCancel={back}
        />
      )}

      {status.enabled && mode === "turning-off" && (
        <TwoStepProofForm
          description="Signing in will need only your password again, and you'll be signed out of your other devices."
          submitLabel="Turn off"
          pendingLabel="Turning off..."
          isPending={disable.isPending}
          error={disable.error}
          onSubmit={async (proof) => {
            await disable.mutateAsync(proof);
            setMode("idle");
          }}
          onCancel={back}
        />
      )}
    </section>
  );
}
