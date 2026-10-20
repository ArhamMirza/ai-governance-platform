import { useState } from "react";

import { useAIUsage } from "../hooks";
import type { UsageSummary } from "../types";

const PERIODS = [7, 30, 90] as const;

const TYPE_LABELS: Record<string, string> = {
  unapproved_site: "Visits to unapproved AI sites",
  blocked_site: "Visits to blocked AI sites",
  dlp_match: "Sensitive data caught",
  request_started: "Tool requests started",
};

function total(summary: UsageSummary, type: string): number {
  return summary.by_type.find((entry) => entry.event_type === type)?.count ?? 0;
}

/** A bar for each day, scaled to the busiest, with the numbers in text so it
 * reads without the picture. */
function DailyBars({ summary }: { summary: UsageSummary }) {
  const busiest = Math.max(1, ...summary.by_day.map((day) => day.unapproved + day.dlp_matches));
  return (
    <ul className="plain-list" aria-label="By day">
      {summary.by_day.map((day) => {
        const sum = day.unapproved + day.dlp_matches;
        return (
          <li key={day.day} className="usage-day">
            <span className="usage-day-label">{day.day}</span>
            <span className="usage-bar" aria-hidden="true">
              <span
                className="usage-bar-fill"
                style={{ width: `${Math.round((sum / busiest) * 100)}%` }}
              />
            </span>
            <span>
              {day.unapproved} site visit{day.unapproved === 1 ? "" : "s"}, {day.dlp_matches} caught
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/** Where the controls are biting: counts only -- never what was typed, which
 * page, or when in the day. */
export function UsagePanel() {
  const [days, setDays] = useState<number>(30);
  const { data: summary, isLoading, isError } = useAIUsage(days);

  return (
    <>
      <div>
        <label htmlFor="usage-period">Period</label>
        <select
          id="usage-period"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          {PERIODS.map((period) => (
            <option key={period} value={period}>
              Last {period} days
            </option>
          ))}
        </select>
      </div>
      {isLoading ? (
        <p>Loading usage...</p>
      ) : isError || !summary ? (
        <p>Failed to load usage.</p>
      ) : summary.by_type.length === 0 ? (
        <p>
          Nothing reported in this period. Counts arrive once browsers have the extension and the
          enrollment key.
        </p>
      ) : (
        <>
          <dl className="usage-totals">
            {Object.keys(TYPE_LABELS)
              .filter((type) => total(summary, type) > 0)
              .map((type) => (
                <div key={type}>
                  <dt>{TYPE_LABELS[type]}</dt>
                  <dd>{total(summary, type)}</dd>
                </div>
              ))}
            {summary.overrides > 0 && (
              <div>
                <dt>Times someone went ahead past a warning</dt>
                <dd>{summary.overrides}</dd>
              </div>
            )}
          </dl>

          <h3>By AI site</h3>
          <table>
            <thead>
              <tr>
                <th>Site</th>
                <th>Unapproved visits</th>
                <th>Blocked</th>
                <th>Sensitive data caught</th>
                <th>Went ahead anyway</th>
              </tr>
            </thead>
            <tbody>
              {summary.by_domain.map((row) => (
                <tr key={row.domain}>
                  <td>
                    {row.tool_name ?? row.domain}
                    <div className="approval-note">{row.domain}</div>
                  </td>
                  <td>{row.unapproved}</td>
                  <td>{row.blocked}</td>
                  <td>{row.dlp_matches}</td>
                  <td>{row.overrides}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {summary.by_rule.length > 0 && (
            <>
              <h3>By rule</h3>
              <table>
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Matches</th>
                    <th>Stopped</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.by_rule.map((row) => (
                    <tr key={row.rule_id}>
                      <td>{row.rule_name ?? `Deleted rule #${row.rule_id}`}</td>
                      <td>{row.matches}</td>
                      <td>{row.blocked}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <h3>By person</h3>
          <table>
            <thead>
              <tr>
                <th>Person</th>
                <th>Unapproved visits</th>
                <th>Sensitive data caught</th>
                <th>Went ahead anyway</th>
              </tr>
            </thead>
            <tbody>
              {summary.by_user.map((row) => (
                <tr key={row.user_ref}>
                  <td>
                    {row.user_name ?? row.user_ref}
                    {row.user_name && <div className="approval-note">{row.user_ref}</div>}
                  </td>
                  <td>{row.unapproved}</td>
                  <td>{row.dlp_matches}</td>
                  <td>{row.overrides}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>By day</h3>
          <DailyBars summary={summary} />
        </>
      )}
    </>
  );
}
