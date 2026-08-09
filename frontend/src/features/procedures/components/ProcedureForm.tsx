import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { usePolicies } from "../../policies/hooks";
import { useCreateProcedure } from "../hooks";

const procedureFormSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  policy_id: z.string().optional(),
});

type ProcedureFormValues = z.infer<typeof procedureFormSchema>;

interface ProcedureFormProps {
  onCreated?: (procedureId: number) => void;
}

export function ProcedureForm({ onCreated }: ProcedureFormProps) {
  const createProcedure = useCreateProcedure();
  const { data: policies } = usePolicies();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProcedureFormValues>({ resolver: zodResolver(procedureFormSchema) });

  const onSubmit = handleSubmit(async (values) => {
    const procedure = await createProcedure.mutateAsync({
      title: values.title,
      description: values.description || null,
      policy_id: values.policy_id ? Number(values.policy_id) : null,
    });
    reset();
    onCreated?.(procedure.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="procedure-title">Title</label>
        <input id="procedure-title" {...register("title")} />
        {errors.title && <p role="alert">{errors.title.message}</p>}
      </div>
      <div>
        <label htmlFor="procedure-description">Description</label>
        <textarea id="procedure-description" {...register("description")} />
      </div>
      <div>
        <label htmlFor="procedure-policy">Implements Policy (optional)</label>
        <select id="procedure-policy" {...register("policy_id")}>
          <option value="">None</option>
          {policies?.map((policy) => (
            <option key={policy.id} value={policy.id}>
              {policy.title}
            </option>
          ))}
        </select>
      </div>
      <p>Documents are added from the procedure's detail page once it's created.</p>
      <button type="submit" disabled={createProcedure.isPending}>
        {createProcedure.isPending ? "Creating..." : "Create Procedure"}
      </button>
    </form>
  );
}
