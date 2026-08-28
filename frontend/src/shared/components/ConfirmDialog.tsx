interface ConfirmDialogProps {
  title: string;
  /** What will happen, including anything that gets deleted alongside it. */
  message: string;
  confirmLabel?: string;
  isPending?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Blocking confirmation for destructive actions. Reuses the modal styling
 * already used by the risk item panel. */
export function ConfirmDialog({
  title,
  message,
  confirmLabel = "Delete",
  isPending = false,
  error = null,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div
        className="modal-panel confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h3>{title}</h3>
            <p>{message}</p>
          </div>
          <button onClick={onCancel} aria-label="Close dialog">
            ×
          </button>
        </div>

        {error && <p role="alert">{error}</p>}

        <div className="confirm-dialog-actions">
          <button onClick={onCancel} disabled={isPending}>
            Cancel
          </button>
          <button className="danger" onClick={onConfirm} disabled={isPending}>
            {isPending ? "Deleting..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
