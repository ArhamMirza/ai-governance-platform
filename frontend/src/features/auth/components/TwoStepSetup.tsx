import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useConfirmTwoStep, useRefreshAccount, useStartTwoStepSetup } from "../hooks";
import type { TwoStepSetup as TwoStepSetupData } from "../types";
import { QrCode } from "./QrCode";
import { RecoveryCodesView } from "./RecoveryCodesView";

const schema = z.object({ code: z.string().trim().min(1, "Enter the code from the app") });
type Values = z.infer<typeof schema>;

/** The key as groups of four, which is easier to type into an app by hand. */
function grouped(secret: string): string {
  return secret.match(/.{1,4}/g)?.join(" ") ?? secret;
}

interface TwoStepSetupProps {
  /** Called once they have confirmed the recovery codes are saved. */
  onDone?: () => void;
  onCancel?: () => void;
}

/** Setting up an authenticator app: start, scan (or type the key), prove it
 * works with one code, then keep the recovery codes. Two-step sign-in is not
 * on until the code is accepted. */
export function TwoStepSetup({ onDone, onCancel }: TwoStepSetupProps) {
  const start = useStartTwoStepSetup();
  const confirm = useConfirmTwoStep();
  const refreshAccount = useRefreshAccount();
  const [setup, setSetup] = useState<TwoStepSetupData | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const begin = async () => {
    try {
      setSetup(await start.mutateAsync());
    } catch {
      // Surfaced below via start.error
    }
  };

  const onSubmit = handleSubmit(async (values) => {
    try {
      const result = await confirm.mutateAsync(values.code);
      setCodes(result.recovery_codes);
      setSetup(null);
    } catch {
      // Surfaced below via confirm.error
    }
  });

  if (codes) {
    return (
      <RecoveryCodesView
        codes={codes}
        onDone={async () => {
          // Only now does the rest of the app learn it is on -- see useConfirmTwoStep.
          await refreshAccount();
          onDone?.();
        }}
      />
    );
  }

  if (!setup) {
    return (
      <div>
        <p>
          You'll need an authenticator app on your phone, such as Google Authenticator, Microsoft
          Authenticator or 1Password. It shows a new 6-digit code every 30 seconds, and you'll
          enter one each time you sign in.
        </p>
        {start.isError && <p role="alert">{readError(start.error, "Couldn't start set-up")}</p>}
        <button type="button" onClick={begin} disabled={start.isPending}>
          {start.isPending ? "Starting..." : "Set up two-step sign-in"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit}>
      <ol className="setup-steps">
        <li>
          <strong>Scan this code</strong> with your authenticator app.
          <div>
            <QrCode value={setup.otpauth_uri} label="QR code for your authenticator app" />
          </div>
        </li>
        <li>
          Can't scan it? Enter this key in the app instead:
          <div>
            <code className="setup-key" data-testid="setup-key">
              {grouped(setup.secret)}
            </code>
          </div>
        </li>
        <li>
          <label htmlFor="setup-code">Enter the 6-digit code the app shows</label>
          <input
            id="setup-code"
            autoComplete="one-time-code"
            inputMode="numeric"
            spellCheck={false}
            {...register("code")}
          />
          {errors.code && <p role="alert">{errors.code.message}</p>}
        </li>
      </ol>

      {confirm.isError && <p role="alert">{readError(confirm.error, "That code didn't work")}</p>}

      <button type="submit" disabled={confirm.isPending}>
        {confirm.isPending ? "Checking..." : "Turn on"}
      </button>
      <button type="button" onClick={() => setSetup(null)}>
        Start again
      </button>
    </form>
  );
}
