interface ShareWithEmployeesProps {
  shared: boolean;
  /** Only an approved record is ever shown to employees, whatever this says. */
  approved: boolean;
  pending: boolean;
  onChange: (shared: boolean) => void;
}

/** Whether employees -- who have no other access to the platform -- can read
 * this on their home page, with its documents. Changing it doesn't touch the
 * approval: it's who can see the record, not what it says. */
export function ShareWithEmployees({ shared, approved, pending, onChange }: ShareWithEmployeesProps) {
  return (
    <div>
      <label htmlFor="share-with-employees">
        <input
          id="share-with-employees"
          type="checkbox"
          checked={shared}
          disabled={pending}
          onChange={(e) => onChange(e.target.checked)}
        />
        Share with employees
      </label>
      <p className="approval-note">
        Employees see it, and every document attached to it, on their home page
        {approved ? "." : " once it's approved."}
      </p>
    </div>
  );
}
