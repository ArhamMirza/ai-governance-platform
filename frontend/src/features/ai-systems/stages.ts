// Mirrors backend/app/core/lifecycle_stages.py, in ISO/IEC 5338 order.
export const STAGES: { key: string; label: string }[] = [
  { key: "inception", label: "Inception" },
  { key: "design", label: "Design" },
  { key: "development", label: "Development" },
  { key: "verification_and_validation", label: "Verification & Validation" },
  { key: "deployment", label: "Deployment" },
  { key: "operation_and_monitoring", label: "Operation & Monitoring" },
  { key: "retirement", label: "Retirement" },
];
