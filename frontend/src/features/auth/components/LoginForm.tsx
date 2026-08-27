import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError } from "../../../shared/api/httpClient";
import { useLogin } from "../hooks";

const loginFormSchema = z.object({
  email: z.string().min(1, "Email is required"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormValues = z.infer<typeof loginFormSchema>;

function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}

export function LoginForm() {
  const login = useLogin();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginFormSchema) });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await login.mutateAsync(values);
    } catch {
      // Surfaced below via login.error
    }
  });

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <h1>Sign in</h1>

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
