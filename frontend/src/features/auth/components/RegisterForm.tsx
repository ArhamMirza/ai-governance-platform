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
  setup_code: z.string().optional(),
});

type RegisterFormValues = z.infer<typeof registerFormSchema>;

interface RegisterFormProps {
  /** Shown only on a real deployment, where the server prints a code at startup. */
  setupCodeRequired?: boolean;
}

export function RegisterForm({ setupCodeRequired = false }: RegisterFormProps) {
  const register = useRegister();
  const {
    register: field,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerFormSchema) });

  const onSubmit = handleSubmit(async (values) => {
    if (setupCodeRequired && !values.setup_code?.trim()) {
      setError("setup_code", { message: "Enter the setup code from the server's log" });
      return;
    }
    try {
      await register.mutateAsync({
        name: values.name,
        email: values.email,
        password: values.password,
        ...(setupCodeRequired ? { setup_code: values.setup_code?.trim() } : {}),
      });
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

      {setupCodeRequired && (
        <div>
          <label htmlFor="register-setup-code">Setup code</label>
          <input
            id="register-setup-code"
            autoComplete="off"
            spellCheck={false}
            aria-describedby="register-setup-code-hint"
            {...field("setup_code")}
          />
          <p id="register-setup-code-hint" className="field-hint">
            Printed in the server's log when it started, or the SETUP_CODE you configured.
          </p>
          {errors.setup_code && <p role="alert">{errors.setup_code.message}</p>}
        </div>
      )}

      {register.isError && <p role="alert">{readError(register.error, "Registration failed")}</p>}

      <button type="submit" disabled={register.isPending}>
        {register.isPending ? "Creating account..." : "Create account"}
      </button>
    </form>
  );
}
