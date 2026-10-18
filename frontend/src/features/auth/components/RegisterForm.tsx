import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useRegister } from "../hooks";
import { MIN_PASSWORD_LENGTH, PASSWORD_HINT, PASSWORD_TOO_SHORT } from "../passwordRules";

const registerFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(3, "Email is required"),
  password: z.string().min(MIN_PASSWORD_LENGTH, PASSWORD_TOO_SHORT),
});

type RegisterFormValues = z.infer<typeof registerFormSchema>;

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
          aria-describedby="register-password-hint"
          {...field("password")}
        />
        <p id="register-password-hint" className="field-hint">
          {PASSWORD_HINT}
        </p>
        {errors.password && <p role="alert">{errors.password.message}</p>}
      </div>

      {register.isError && <p role="alert">{readError(register.error, "Registration failed")}</p>}

      <button type="submit" disabled={register.isPending}>
        {register.isPending ? "Creating account..." : "Create account"}
      </button>
    </form>
  );
}
