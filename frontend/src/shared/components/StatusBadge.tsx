interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className="status-badge" data-status={status}>{status.replace(/_/g, " ")}</span>;
}
