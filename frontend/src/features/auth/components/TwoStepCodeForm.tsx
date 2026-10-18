import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useLoginTwoStep } from "../hooks";

const schema = z.object({ code: z.string().trim().min(1, "Enter the code") });
type Values = z.infer<typeof schema>;

interface TwoStepCodeFormProps {
  ticket: string;
  /** Back to the password step. */
  onBack: () => void;
}

/** The second step of signing in: the six digits from the authenticator app,
 * or one of the recovery codes kept for when it isn't to hand. */
export function TwoStepCodeForm({ ticket, onBack }: TwoStepCodeFormProps) {
  const verify = useLoginTwoStep();
  const [usingRecovery, setUsingRecovery] = useState(false);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await verify.mutateAsync({ ticket, code: values.code });
    } catch {
      // Surfaced below via verify.error
    }
  });

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <h1>Two-step sign-in</h1>
      <p>
        {usingRecovery
          ? "Enter one of your recovery codes. Each works once."
          : "Enter the 6-digit code from your authenticator app."}
      </p>

      <div>
        <label htmlFor="two-step-code">{usingRecovery ? "Recovery code" : "Authentication code"}</label>
        <input
          id="two-step-code"
          key={usingRecovery ? "recovery" : "code"}
          autoComplete="one-time-code"
          autoCapitalize="off"
          spellCheck={false}
          inputMode={usingRecovery ? "text" : "numeric"}
          // eslint-disable-next-line jsx-a11y/no-autofocus -- it is the only field on the step
          autoFocus
          {...register("code")}
        />
        {errors.code && <p role="alert">{errors.code.message}</p>}
      </div>

      {verify.isError && <p role="alert">{readError(verify.error, "Sign in failed")}</p>}

      <button type="submit" disabled={verify.isPending}>
        {verify.isPending ? "Checking..." : "Verify"}
      </button>

      <p>
        <button
          type="button"
          className="link-button"
          onClick={() => {
            setUsingRecovery((value) => !value);
            reset();
          }}
        >
          {usingRecovery ? "Use my authenticator app instead" : "Use a recovery code instead"}
        </button>
      </p>
      <p>
        <button type="button" className="link-button" onClick={onBack}>
          Back to password
        </button>
      </p>
    </form>
  );
}
