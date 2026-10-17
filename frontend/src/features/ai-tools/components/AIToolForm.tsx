import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useCreateAITool } from "../hooks";
import { splitDomains } from "../labels";

const aiToolFormSchema = z.object({
  name: z.string().trim().min(1, "What is the tool called?"),
  vendor: z.string(),
  domains: z.string().refine((text) => splitDomains(text).length > 0, "Add at least one address"),
  description: z.string(),
});

type AIToolFormValues = z.infer<typeof aiToolFormSchema>;

interface AIToolFormProps {
  onCreated?: (toolId: number) => void;
}

/** Adds a tool to the register as "not approved". Approving it is the Chief
 * AI Governance Officer's decision, made on the tool's page. */
export function AIToolForm({ onCreated }: AIToolFormProps) {
  const createTool = useCreateAITool();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AIToolFormValues>({
    resolver: zodResolver(aiToolFormSchema),
    defaultValues: { name: "", vendor: "", domains: "", description: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    const tool = await createTool.mutateAsync({
      name: values.name,
      vendor: values.vendor.trim() || null,
      domains: splitDomains(values.domains),
      description: values.description.trim() || null,
      owner_id: null,
      supplier_id: null,
    });
    reset();
    onCreated?.(tool.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="ai-tool-name">Tool</label>
        <input id="ai-tool-name" {...register("name")} />
        {errors.name && <p role="alert">{errors.name.message}</p>}
      </div>
      <div>
        <label htmlFor="ai-tool-vendor">Vendor</label>
        <input id="ai-tool-vendor" {...register("vendor")} />
      </div>
      <div>
        <label htmlFor="ai-tool-domains">Addresses</label>
        <textarea
          id="ai-tool-domains"
          placeholder={"chat.example.com\napp.example.com"}
          {...register("domains")}
        />
        <p className="approval-note">
          The sites the tool is used at, one per line. A web address is fine; only the domain is kept.
        </p>
        {errors.domains && <p role="alert">{errors.domains.message}</p>}
      </div>
      <div>
        <label htmlFor="ai-tool-description">What it is</label>
        <textarea id="ai-tool-description" {...register("description")} />
      </div>
      {createTool.isError && (
        <p role="alert">{readError(createTool.error, "Failed to add the tool.")}</p>
      )}
      <button type="submit" disabled={createTool.isPending}>
        {createTool.isPending ? "Adding..." : "Add Tool"}
      </button>
    </form>
  );
}
