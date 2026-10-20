import { useAICoverage } from "../hooks";
import type { CoveragePerson } from "../types";

const WINDOW_DAYS = 7;

const STATUS_LABELS: Record<CoveragePerson["status"], string> = {
  reporting: "Reporting",
  quiet: "Gone quiet",
  never: "Never reported",
};

/** Who has the extension and is reaching the platform. Judged from a daily
 * check-in, so it says "this browser is connected", not "this person is not
 * using AI" -- a quiet browser may simply be switched off, or on leave. */
export function CoveragePanel() {
  const { data: coverage, isLoading, isError } = useAICoverage(WINDOW_DAYS);

  return (
    <section aria-labelledby="coverage-heading">
      <h2 id="coverage-heading">Who has the extension</h2>
      {isLoading ? (
        <p>Loading coverage...</p>
      ) : isError || !coverage ? (
        <p>Failed to load coverage.</p>
      ) : coverage.active_people === 0 ? (
        <p>There are no active accounts yet.</p>
      ) : (
        <>
          <p>
            <strong>
              {coverage.reporting} of {coverage.active_people}
            </strong>{" "}
            {coverage.active_people === 1 ? "person has" : "people have"} a
            browser that reported in the last {coverage.days} days.
          </p>
          {coverage.reporting < coverage.active_people && (
            <>
              <h3>People whose browser has not reported</h3>
              <table>
                <thead>
                  <tr>
                    <th>Person</th>
                    <th>Status</th>
                    <th>Last reported</th>
                  </tr>
                </thead>
                <tbody>
                  {coverage.people
                    .filter((person) => person.status !== "reporting")
                    .map((person) => (
                      <tr key={person.user_id}>
                        <td>
                          {person.name}
                          <div className="approval-note">{person.email}</div>
                        </td>
                        <td>{STATUS_LABELS[person.status]}</td>
                        <td>{person.last_seen ?? "Never"}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </>
          )}
          {coverage.unmatched_reporters > 0 && (
            <p className="approval-note">
              {coverage.unmatched_reporters} other browser
              {coverage.unmatched_reporters === 1 ? "" : "s"} reported in under
              an address that matches no account here, such as a personal
              profile or an unsigned one.
            </p>
          )}
        </>
      )}
    </section>
  );
}
