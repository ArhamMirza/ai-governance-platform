import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCreatePolicy } from "../hooks";

const policyFormSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
});

type PolicyFormValues = z.infer<typeof policyFormSchema>;

interface PolicyFormProps {
  onCreated?: (policyId: number) => void;
}

export function PolicyForm({ onCreated }: PolicyFormProps) {
  const createPolicy = useCreatePolicy();
  const { data: directory } = useUserDirectory();
  const [ownerId, setOwnerId] = useState("");
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
      owner_id: ownerId ? Number(ownerId) : null,
    });
    reset();
    setOwnerId("");
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
        <label htmlFor="policy-owner">Owner</label>
        <select id="policy-owner" value={ownerId} onChange={(e) => setOwnerId(e.target.value)}>
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <p>Documents are added from the policy's detail page once it's created.</p>
      <button type="submit" disabled={createPolicy.isPending}>
        {createPolicy.isPending ? "Creating..." : "Create Policy"}
      </button>
    </form>
  );
}
