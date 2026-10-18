import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useChangePassword } from "../hooks";
import { MIN_PASSWORD_LENGTH, PASSWORD_HINT, PASSWORD_TOO_SHORT } from "../passwordRules";

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: z.string().min(MIN_PASSWORD_LENGTH, PASSWORD_TOO_SHORT),
    confirm_password: z.string(),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    path: ["confirm_password"],
    message: "The two new passwords don't match",
  });

type ChangePasswordValues = z.infer<typeof changePasswordSchema>;

interface ChangePasswordFormProps {
  /** True on the screen shown before anything else is allowed: the wording
   * says why, and there's nothing else on the page. */
  forced?: boolean;
  onChanged?: () => void;
}

export function ChangePasswordForm({ forced = false, onChanged }: ChangePasswordFormProps) {
  const changePassword = useChangePassword();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ChangePasswordValues>({ resolver: zodResolver(changePasswordSchema) });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await changePassword.mutateAsync({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      reset();
      onChanged?.();
    } catch {
      // Surfaced below via changePassword.error
    }
  });

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <h1>{forced ? "Choose a new password" : "Change your password"}</h1>
      <p>
        {forced
          ? "The password you signed in with was set by someone else, or no longer meets our rules. Choose your own to continue."
          : "Other devices you're signed in on will be signed out."}
      </p>

      <div>
        <label htmlFor="current-password">Current password</label>
        <input
          id="current-password"
          type="password"
          autoComplete="current-password"
          {...register("current_password")}
        />
        {errors.current_password && <p role="alert">{errors.current_password.message}</p>}
      </div>
      <div>
        <label htmlFor="new-password">New password</label>
        <input
          id="new-password"
          type="password"
          autoComplete="new-password"
          aria-describedby="new-password-hint"
          {...register("new_password")}
        />
        <p id="new-password-hint" className="field-hint">
          {PASSWORD_HINT}
        </p>
        {errors.new_password && <p role="alert">{errors.new_password.message}</p>}
      </div>
      <div>
        <label htmlFor="confirm-password">Confirm new password</label>
        <input
          id="confirm-password"
          type="password"
          autoComplete="new-password"
          {...register("confirm_password")}
        />
        {errors.confirm_password && <p role="alert">{errors.confirm_password.message}</p>}
      </div>

      {changePassword.isError && (
        <p role="alert">{readError(changePassword.error, "Couldn't change the password")}</p>
      )}
      {changePassword.isSuccess && !forced && <p role="status">Password changed.</p>}

      <button type="submit" disabled={changePassword.isPending}>
        {changePassword.isPending ? "Saving..." : "Change password"}
      </button>
    </form>
  );
}
