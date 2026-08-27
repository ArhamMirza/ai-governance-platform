import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError } from "../../../shared/api/httpClient";
import { useRegister } from "../hooks";

const registerFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(3, "Email is required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type RegisterFormValues = z.infer<typeof registerFormSchema>;

function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}

export function RegisterForm() {
  const register = useRegister();
  const {
    register: field,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerFormSchema) });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await register.mutateAsync(values);
    } catch {
      // Surfaced below via register.error
    }
  });

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <h1>Create your account</h1>
      <p>This is a one-time setup -- no other accounts can be created after this.</p>

      <div>
        <label htmlFor="register-name">Name</label>
        <input id="register-name" autoComplete="name" {...field("name")} />
        {errors.name && <p role="alert">{errors.name.message}</p>}
      </div>
      <div>
        <label htmlFor="register-email">Email</label>
        <input id="register-email" type="email" autoComplete="email" {...field("email")} />
        {errors.email && <p role="alert">{errors.email.message}</p>}
      </div>
      <div>
        <label htmlFor="register-password">Password</label>
        <input
          id="register-password"
          type="password"
          autoComplete="new-password"
          {...field("password")}
        />
        {errors.password && <p role="alert">{errors.password.message}</p>}
      </div>

      {register.isError && <p role="alert">{readError(register.error, "Registration failed")}</p>}

      <button type="submit" disabled={register.isPending}>
        {register.isPending ? "Creating account..." : "Create account"}
      </button>
    </form>
  );
}
