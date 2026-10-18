import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useLogin } from "../hooks";
import { isMfaChallenge } from "../types";
import { TwoStepCodeForm } from "./TwoStepCodeForm";

const loginFormSchema = z.object({
  email: z.string().min(1, "Email is required"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormValues = z.infer<typeof loginFormSchema>;

export function LoginForm() {
  const login = useLogin();
  // Set when the password was right for an account with two-step sign-in.
  const [ticket, setTicket] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    resetField,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginFormSchema) });

  const onSubmit = handleSubmit(async (values) => {
    try {
      const result = await login.mutateAsync(values);
      if (result && isMfaChallenge(result)) setTicket(result.ticket);
    } catch {
      // Surfaced below via login.error
    }
  });

  if (ticket) {
    return (
      <TwoStepCodeForm
        ticket={ticket}
        onBack={() => {
          setTicket(null);
          // Keep the email for the next try, but not the password.
          resetField("password");
        }}
      />
    );
  }

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <h1>Sign in</h1>
      <p>Continue to your organization's register.</p>

      <div>
        <label htmlFor="login-email">Email</label>
        <input id="login-email" type="email" autoComplete="email" {...register("email")} />
        {errors.email && <p role="alert">{errors.email.message}</p>}
      </div>
      <div>
        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          {...register("password")}
        />
        {errors.password && <p role="alert">{errors.password.message}</p>}
      </div>

      {login.isError && <p role="alert">{readError(login.error, "Sign in failed")}</p>}

      <button type="submit" disabled={login.isPending}>
        {login.isPending ? "Signing in..." : "Sign in"}
      </button>
    </form>
  );
}
