import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useCreatePolicy } from "../hooks";

const policyFormSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  content: z.string().optional(),
});

type PolicyFormValues = z.infer<typeof policyFormSchema>;

interface PolicyFormProps {
  onCreated?: (policyId: number) => void;
}

export function PolicyForm({ onCreated }: PolicyFormProps) {
  const createPolicy = useCreatePolicy();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PolicyFormValues>({ resolver: zodResolver(policyFormSchema) });

  const onSubmit = handleSubmit(async (values) => {
    const policy = await createPolicy.mutateAsync({
      title: values.title,
      description: values.description || null,
      content: values.content ?? "",
    });
    reset();
    onCreated?.(policy.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="policy-title">Title</label>
        <input id="policy-title" {...register("title")} />
        {errors.title && <p role="alert">{errors.title.message}</p>}
      </div>
      <div>
        <label htmlFor="policy-description">Description</label>
        <textarea id="policy-description" {...register("description")} />
      </div>
      <div>
        <label htmlFor="policy-content">Content</label>
        <textarea id="policy-content" {...register("content")} />
      </div>
      <button type="submit" disabled={createPolicy.isPending}>
        {createPolicy.isPending ? "Creating..." : "Create Policy"}
      </button>
    </form>
  );
}
