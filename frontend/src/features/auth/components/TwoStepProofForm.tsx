import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import type { TwoStepProof } from "../types";

const schema = z.object({
  password: z.string().min(1, "Enter your password"),
  code: z.string().trim().min(1, "Enter a code from your app, or a recovery code"),
});

interface TwoStepProofFormProps {
  submitLabel: string;
  pendingLabel: string;
  /** What is about to happen, so the person knows why they're asked again. */
  description: string;
  isPending: boolean;
  error: unknown;
  onSubmit: (proof: TwoStepProof) => Promise<void>;
  onCancel: () => void;
}

/** Turning it off, or making new recovery codes, asks for the password and a
 * current code, so someone at an unlocked laptop can't do either. */
export function TwoStepProofForm({
  submitLabel,
  pendingLabel,
  description,
  isPending,
  error,
  onSubmit,
  onCancel,
}: TwoStepProofFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TwoStepProof>({ resolver: zodResolver(schema) });

  const submit = handleSubmit(async (values) => {
    try {
      await onSubmit(values);
    } catch {
      // Surfaced below via `error`
    }
  });

  return (
    <form onSubmit={submit}>
      <p>{description}</p>
      <div>
        <label htmlFor="proof-password">Your password</label>
        <input
          id="proof-password"
          type="password"
          autoComplete="current-password"
          {...register("password")}
        />
        {errors.password && <p role="alert">{errors.password.message}</p>}
      </div>
      <div>
        <label htmlFor="proof-code">Code from your app, or a recovery code</label>
        <input
          id="proof-code"
          autoComplete="one-time-code"
          spellCheck={false}
          {...register("code")}
        />
        {errors.code && <p role="alert">{errors.code.message}</p>}
      </div>
      {error != null && <p role="alert">{readError(error, "That didn't work")}</p>}
      <button type="submit" disabled={isPending}>
        {isPending ? pendingLabel : submitLabel}
      </button>
      <button type="button" onClick={onCancel}>
        Cancel
      </button>
    </form>
  );
}
