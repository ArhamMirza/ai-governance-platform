import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useCreateUser } from "../hooks";

const userFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(3, "Email is required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  role: z.enum(["admin", "contributor", "viewer"]),
});

type UserFormValues = z.infer<typeof userFormSchema>;

interface UserFormProps {
  onCreated?: () => void;
}

export function UserForm({ onCreated }: UserFormProps) {
  const createUser = useCreateUser();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<UserFormValues>({
    resolver: zodResolver(userFormSchema),
    defaultValues: { role: "contributor" },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await createUser.mutateAsync(values);
      reset();
      onCreated?.();
    } catch {
      // Surfaced below via createUser.error
    }
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="user-name">Name</label>
        <input id="user-name" autoComplete="name" {...register("name")} />
        {errors.name && <p role="alert">{errors.name.message}</p>}
      </div>
      <div>
        <label htmlFor="user-email">Email</label>
        <input id="user-email" type="email" autoComplete="email" {...register("email")} />
        {errors.email && <p role="alert">{errors.email.message}</p>}
      </div>
      <div>
        <label htmlFor="user-password">Temporary password</label>
        <input
          id="user-password"
          type="password"
          autoComplete="new-password"
          {...register("password")}
        />
        {errors.password && <p role="alert">{errors.password.message}</p>}
      </div>
      <div>
        <label htmlFor="user-role">Role</label>
        <select id="user-role" {...register("role")}>
          <option value="viewer">Viewer</option>
          <option value="contributor">Contributor</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      {createUser.isError && (
        <p role="alert">{readError(createUser.error, "Failed to create user")}</p>
      )}

      <button type="submit" disabled={createUser.isPending}>
        {createUser.isPending ? "Creating..." : "Create User"}
      </button>
    </form>
  );
}
