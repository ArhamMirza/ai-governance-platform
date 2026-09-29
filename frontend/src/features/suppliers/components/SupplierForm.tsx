import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCreateSupplier } from "../hooks";
import { SUPPLIER_TYPE_OPTIONS } from "../labels";

const supplierFormSchema = z
  .object({
    name: z.string().min(1, "Name is required"),
    supplier_type: z.enum([
      "model_provider",
      "data_provider",
      "infrastructure",
      "software",
      "services",
      "other",
    ]),
    description: z.string(),
    owner_id: z.string(),
    contract_reference: z.string(),
    contract_start: z.string(),
    contract_end: z.string(),
  })
  .refine(
    (values) =>
      !values.contract_start || !values.contract_end || values.contract_end >= values.contract_start,
    { message: "The contract can't end before it starts", path: ["contract_end"] },
  );

type SupplierFormValues = z.infer<typeof supplierFormSchema>;

interface SupplierFormProps {
  onCreated?: (supplierId: number) => void;
}

/** The register entry itself -- responsibilities, requirements, the review
 * schedule and linked AI systems are filled in on the detail page. */
export function SupplierForm({ onCreated }: SupplierFormProps) {
  const createSupplier = useCreateSupplier();
  const { data: directory } = useUserDirectory();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SupplierFormValues>({
    resolver: zodResolver(supplierFormSchema),
    defaultValues: {
      supplier_type: "model_provider",
      description: "",
      owner_id: "",
      contract_reference: "",
      contract_start: "",
      contract_end: "",
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    const supplier = await createSupplier.mutateAsync({
      name: values.name,
      supplier_type: values.supplier_type,
      description: values.description || null,
      owner_id: values.owner_id ? Number(values.owner_id) : null,
      contract_reference: values.contract_reference || null,
      contract_start: values.contract_start || null,
      contract_end: values.contract_end || null,
    });
    reset();
    onCreated?.(supplier.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="supplier-name">Name</label>
        <input id="supplier-name" {...register("name")} />
        {errors.name && <p role="alert">{errors.name.message}</p>}
      </div>
      <div>
        <label htmlFor="supplier-type">Type</label>
        <select id="supplier-type" {...register("supplier_type")}>
          {SUPPLIER_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="supplier-description">What they supply</label>
        <textarea id="supplier-description" {...register("description")} />
      </div>
      <div>
        <label htmlFor="supplier-owner">Relationship owner</label>
        <select id="supplier-owner" {...register("owner_id")}>
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="supplier-contract-reference">Contract reference</label>
        <input id="supplier-contract-reference" {...register("contract_reference")} />
      </div>
      <div>
        <label htmlFor="supplier-contract-start">Contract start</label>
        <input id="supplier-contract-start" type="date" {...register("contract_start")} />
      </div>
      <div>
        <label htmlFor="supplier-contract-end">Contract end</label>
        <input id="supplier-contract-end" type="date" {...register("contract_end")} />
        {errors.contract_end && <p role="alert">{errors.contract_end.message}</p>}
      </div>
      <button type="submit" disabled={createSupplier.isPending}>
        {createSupplier.isPending ? "Adding..." : "Add Supplier"}
      </button>
    </form>
  );
}
