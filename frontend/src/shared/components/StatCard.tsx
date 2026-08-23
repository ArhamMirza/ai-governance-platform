import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "danger" | "warning" | "success";
  children?: ReactNode;
}

export function StatCard({ label, value, hint, tone = "default", children }: StatCardProps) {
  return (
    <div className="stat-card" data-tone={tone}>
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value">{value}</div>
      {hint && <div className="stat-card-hint">{hint}</div>}
      {children}
    </div>
  );
}
