import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../../../shared/api/httpClient";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useDeleteSupplier,
  useDeleteSupplierReview,
  useRecordSupplierReview,
  useSetSupplierAISystems,
  useSupplier,
  useUpdateSupplier,
} from "../hooks";
import { REVIEW_OUTCOME_OPTIONS, SUPPLIER_TYPE_OPTIONS } from "../labels";
import type {
  SupplierDetail as SupplierDetailData,
  SupplierReviewOutcome,
  SupplierStatus,
  SupplierType,
} from "../types";
import { SupplierFlags } from "./SupplierFlags";

interface SupplierDetailProps {
  supplierId: number;
}

type TextField =
  | "description"
  | "contact_name"
  | "contact_email"
  | "contract_reference"
  | "responsibilities"
  | "requirements";

const SHORT_TEXT_FIELDS: { key: TextField; label: string }[] = [
  { key: "contact_name", label: "Contact name" },
  { key: "contact_email", label: "Contact email" },
  { key: "contract_reference", label: "Contract reference" },
];

const LONG_TEXT_FIELDS: { key: TextField; label: string }[] = [
  { key: "description", label: "What they supply" },
  { key: "responsibilities", label: "Responsibilities (who does what, A.10.2)" },
  { key: "requirements", label: "Requirements of the supplier (A.10.3)" },
];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Interval and first-review date are saved together -- the server refuses
 * one without the other. */
function ReviewScheduleForm({ supplier }: { supplier: SupplierDetailData }) {
  const updateSupplier = useUpdateSupplier(supplier.id);
  const [interval, setInterval] = useState(supplier.review_interval_months?.toString() ?? "");
  const [firstDue, setFirstDue] = useState(supplier.first_review_due ?? "");
  const complete = (interval === "") === (firstDue === "");

  return (
    <div>
      <label htmlFor="supplier-review-interval">Review every (months)</label>
      <input
        id="supplier-review-interval"
        type="number"
        min={1}
        value={interval}
        onChange={(e) => setInterval(e.target.value)}
      />
      <label htmlFor="supplier-first-review-due">First review due</label>
      <input
        id="supplier-first-review-due"
        type="date"
        value={firstDue}
        onChange={(e) => setFirstDue(e.target.value)}
      />
      <button
        onClick={() =>
          updateSupplier.mutate({
            review_interval_months: interval ? Number(interval) : null,
            first_review_due: firstDue || null,
          })
        }
        disabled={!complete || updateSupplier.isPending}
      >
        Save schedule
      </button>
      {!complete && <p className="approval-note">Set both, or clear both for no reviews.</p>}
    </div>
  );
}

function AddReviewForm({ supplierId }: { supplierId: number }) {
  const recordReview = useRecordSupplierReview(supplierId);
  const [reviewDate, setReviewDate] = useState(todayIso());
  const [outcome, setOutcome] = useState<SupplierReviewOutcome>("satisfactory");
  const [notes, setNotes] = useState("");

  const submit = async () => {
    await recordReview.mutateAsync({ review_date: reviewDate, outcome, notes: notes || null });
    setNotes("");
  };

  return (
    <div className="inline-form">
      <label htmlFor="supplier-review-date">Review date</label>
      <input
        id="supplier-review-date"
        type="date"
        max={todayIso()}
        value={reviewDate}
        onChange={(e) => setReviewDate(e.target.value)}
      />
      <label htmlFor="supplier-review-outcome">Outcome</label>
      <select
        id="supplier-review-outcome"
        value={outcome}
        onChange={(e) => setOutcome(e.target.value as SupplierReviewOutcome)}
      >
        {REVIEW_OUTCOME_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <label htmlFor="supplier-review-notes">Notes</label>
      <input
        id="supplier-review-notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <button onClick={submit} disabled={!reviewDate || recordReview.isPending}>
        Record Review
      </button>
      {recordReview.isError && (
        <p role="alert">
          {recordReview.error instanceof ApiError
            ? recordReview.error.message
            : "Failed to record the review."}
        </p>
      )}
    </div>
  );
}

export function SupplierDetail({ supplierId }: SupplierDetailProps) {
  const { data: supplier, isLoading, isError } = useSupplier(supplierId);
  const { data: inventory } = useAISystemInventoryRows();
  const { data: directory } = useUserDirectory();
  const updateSupplier = useUpdateSupplier(supplierId);
  const setAISystems = useSetSupplierAISystems(supplierId);
  const deleteSupplier = useDeleteSupplier();
  const deleteReview = useDeleteSupplierReview();
  const navigate = useNavigate();
  const [openEvidence, setOpenEvidence] = useState<number | null>(null);

  if (isLoading) return <p>Loading supplier...</p>;
  if (isError || !supplier) return <p>Failed to load supplier.</p>;

  const toggleAISystem = (rowId: number, linked: boolean) => {
    const next = linked
      ? [...supplier.ai_system_row_ids, rowId]
      : supplier.ai_system_row_ids.filter((id) => id !== rowId);
    setAISystems.mutate(next);
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete ${supplier.name} and its reviews?`)) return;
    await deleteSupplier.mutateAsync(supplierId);
    navigate("/suppliers");
  };

  const textInput = ({ key, label }: { key: TextField; label: string }, multiline: boolean) => {
    const props = {
      id: `supplier-${key}`,
      defaultValue: supplier[key] ?? "",
      onBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (e.target.value !== (supplier[key] ?? "")) {
          updateSupplier.mutate({ [key]: e.target.value || null });
        }
      },
    };
    return (
      <div key={key}>
        <label htmlFor={props.id}>{label}</label>
        {multiline ? <textarea {...props} /> : <input {...props} />}
      </div>
    );
  };

  return (
    <article>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{supplier.name}</h2>
          <StatusBadge status={supplier.status} />
          <SupplierFlags supplier={supplier} />
        </div>
      </header>

      <div>
        <label htmlFor="supplier-status-edit">Status</label>
        <select
          id="supplier-status-edit"
          value={supplier.status}
          onChange={(e) => updateSupplier.mutate({ status: e.target.value as SupplierStatus })}
        >
          <option value="active">Active</option>
          <option value="inactive">No longer used</option>
        </select>
      </div>
      <div>
        <label htmlFor="supplier-type-edit">Type</label>
        <select
          id="supplier-type-edit"
          value={supplier.supplier_type}
          onChange={(e) =>
            updateSupplier.mutate({ supplier_type: e.target.value as SupplierType })
          }
        >
          {SUPPLIER_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="supplier-owner-edit">Relationship owner</label>
        <select
          id="supplier-owner-edit"
          value={supplier.owner_id ?? ""}
          onChange={(e) =>
            updateSupplier.mutate({ owner_id: e.target.value ? Number(e.target.value) : null })
          }
        >
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>

      {SHORT_TEXT_FIELDS.map((field) => textInput(field, false))}

      <div>
        <label htmlFor="supplier-contract-start-edit">Contract start</label>
        <input
          id="supplier-contract-start-edit"
          type="date"
          value={supplier.contract_start ?? ""}
          onChange={(e) => updateSupplier.mutate({ contract_start: e.target.value || null })}
        />
      </div>
      <div>
        <label htmlFor="supplier-contract-end-edit">Contract end</label>
        <input
          id="supplier-contract-end-edit"
          type="date"
          value={supplier.contract_end ?? ""}
          onChange={(e) => updateSupplier.mutate({ contract_end: e.target.value || null })}
        />
      </div>
      {updateSupplier.isError && (
        <p role="alert">
          {updateSupplier.error instanceof ApiError
            ? updateSupplier.error.message
            : "Failed to save the supplier."}
        </p>
      )}

      {LONG_TEXT_FIELDS.map((field) => textInput(field, true))}

      <section>
        <h3>AI Systems</h3>
        <p>Which AI systems this supplier contributes to.</p>
        {(inventory?.rows ?? []).length === 0 ? (
          <p>No AI systems in the inventory yet.</p>
        ) : (
          <ul className="checkbox-list">
            {(inventory?.rows ?? []).map((row) => {
              const name =
                typeof row.data.name === "string" && row.data.name
                  ? row.data.name
                  : `System #${row.id}`;
              return (
                <li key={row.id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={supplier.ai_system_row_ids.includes(row.id)}
                      onChange={(e) => toggleAISystem(row.id, e.target.checked)}
                      disabled={setAISystems.isPending}
                    />
                    {name}
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section>
        <h3>Reviews</h3>
        <ReviewScheduleForm key={supplier.updated_at} supplier={supplier} />
        {supplier.next_review_due && <p>Next review due {supplier.next_review_due}.</p>}
        <AddReviewForm supplierId={supplierId} />
        {supplier.reviews.length === 0 ? (
          <p>No reviews recorded yet.</p>
        ) : (
          <ul className="completion-history">
            {supplier.reviews.map((review) => (
              <li key={review.id}>
                <span>
                  {review.review_date}: <StatusBadge status={review.outcome} />
                  {review.notes && ` ${review.notes}`}
                </span>
                <button
                  onClick={() => setOpenEvidence((open) => (open === review.id ? null : review.id))}
                >
                  {openEvidence === review.id ? "Hide documents" : "Documents"}
                </button>
                <button
                  onClick={() => deleteReview.mutate(review.id)}
                  disabled={deleteReview.isPending}
                >
                  Delete
                </button>
                {openEvidence === review.id && (
                  <DocumentBrowser entityType="SupplierReview" entityId={review.id} />
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <h3>Contracts &amp; Agreements</h3>
      <DocumentBrowser entityType="Supplier" entityId={supplierId} />

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="Supplier" entityId={supplierId} />

      <AuditLogViewer entityType="Supplier" entityId={supplierId} />

      <div className="detail-actions">
        <button onClick={handleDelete} disabled={deleteSupplier.isPending}>
          Delete Supplier
        </button>
      </div>
    </article>
  );
}
