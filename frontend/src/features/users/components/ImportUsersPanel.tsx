import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { usePreviewUserImport, useRunUserImport } from "../hooks";
import type {
  ImportAction,
  UserImportCreated,
  UserImportPreview,
  UserImportResult,
} from "../types";

const ACTION_LABELS: Record<ImportAction, string> = {
  create: "Add",
  update: "Update",
  unchanged: "No change",
  skip: "Skipped",
};

const TEMPLATE =
  "name,email,role\nElena Ortiz,elena.ortiz@example.com,employee\n";

/** A spreadsheet treats a cell that starts with one of these as a formula. */
function safeCell(value: string): string {
  const text = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return `"${text.replace(/"/g, '""')}"`;
}

function passwordsCsv(created: UserImportCreated[], expiresOn: string): string {
  const lines = created.map((person) =>
    [
      person.name,
      person.email,
      person.role,
      person.temporary_password,
      expiresOn,
    ]
      .map(safeCell)
      .join(","),
  );
  return (
    ["name,email,role,temporary password,works until", ...lines].join("\n") +
    "\n"
  );
}

function download(filename: string, text: string) {
  const url = URL.createObjectURL(
    new Blob([text], { type: "text/csv;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function PreviewTable({ preview }: { preview: UserImportPreview }) {
  return (
    <>
      <p>
        <strong>{preview.create}</strong> to add,{" "}
        <strong>{preview.update}</strong> to update, {preview.unchanged} already
        up to date, {preview.skip} skipped.
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Line</th>
              <th>Person</th>
              <th>Role</th>
              <th>What happens</th>
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((row) => (
              <tr key={row.line}>
                <td>{row.line}</td>
                <td>
                  {row.name || "(no name)"}
                  <div className="approval-note">
                    {row.email || "(no email)"}
                  </div>
                </td>
                <td>{row.role ?? ""}</td>
                <td>
                  {ACTION_LABELS[row.action]}
                  {row.note && <div className="approval-note">{row.note}</div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function MissingFromFile({
  people,
}: {
  people: UserImportPreview["missing_from_file"];
}) {
  if (people.length === 0) return null;
  return (
    <>
      <h3>In the system but not in this file</h3>
      <p className="approval-note">
        Nothing is done about these. If someone has left, deactivate them from
        the list below.
      </p>
      <ul className="plain-list">
        {people.map((person) => (
          <li key={person.id}>
            {person.name} <span className="approval-note">{person.email}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

function Passwords({
  result,
  onDone,
}: {
  result: UserImportResult;
  onDone: () => void;
}) {
  return (
    <div role="status">
      <h3>
        {result.created.length} account{result.created.length === 1 ? "" : "s"}{" "}
        added
        {result.updated > 0 && `, ${result.updated} updated`}
      </h3>
      {result.created.length > 0 && (
        <>
          <p className="reporter-concern">
            These starting passwords are shown <strong>once</strong>. Save the
            file now and give each person theirs privately, then delete the
            file. They must choose their own at first sign-in, and an unused one
            stops working on {result.password_expires_on}.
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Person</th>
                  <th>Role</th>
                  <th>Starting password</th>
                </tr>
              </thead>
              <tbody>
                {result.created.map((person) => (
                  <tr key={person.email}>
                    <td>
                      {person.name}
                      <div className="approval-note">{person.email}</div>
                    </td>
                    <td>{person.role}</td>
                    <td>
                      <code className="temporary-password">
                        {person.temporary_password}
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="import-actions">
            <button
              onClick={() =>
                download(
                  "starting-passwords.csv",
                  passwordsCsv(result.created, result.password_expires_on),
                )
              }
            >
              Download as CSV
            </button>
          </div>
        </>
      )}
      {result.skipped.length > 0 && (
        <>
          <h3>Not imported</h3>
          <ul className="plain-list">
            {result.skipped.map((row) => (
              <li key={row.line}>
                Line {row.line}: {row.email || row.name || "(blank)"} &mdash;{" "}
                {row.note}
              </li>
            ))}
          </ul>
        </>
      )}
      <MissingFromFile people={result.missing_from_file} />
      <div className="import-actions">
        <button onClick={onDone}>Done</button>
      </div>
    </div>
  );
}

/** Adds and updates staff accounts from a CSV: preview first, then import. */
export function ImportUsersPanel({ onClose }: { onClose: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const preview = usePreviewUserImport();
  const importer = useRunUserImport();

  // The result, with its passwords, lives only here and goes when this does.
  const result = importer.data;
  const previewed = preview.data;

  const choose = (next: File | null) => {
    setFile(next);
    setError(null);
    preview.reset();
  };

  const showPreview = async () => {
    if (!file) return;
    setError(null);
    try {
      await preview.mutateAsync(file);
    } catch (err) {
      setError(readError(err, "Couldn't read that file."));
    }
  };

  const runImport = async () => {
    if (!file) return;
    setError(null);
    try {
      await importer.mutateAsync(file);
    } catch (err) {
      setError(readError(err, "The import failed."));
    }
  };

  const close = () => {
    importer.reset();
    preview.reset();
    onClose();
  };

  if (result) return <Passwords result={result} onDone={close} />;

  const changes = previewed ? previewed.create + previewed.update : 0;

  return (
    <section aria-label="Import people from a CSV" className="import-panel">
      <h2>Import people from a CSV</h2>
      <p>
        One row per person, with columns <code>name</code>, <code>email</code>{" "}
        and optionally <code>role</code> (<code>contributor</code>,{" "}
        <code>viewer</code> or <code>employee</code>; blank means employee).
        People are matched on email, so you can upload a corrected file again.
        Administrators are never created or changed from a file.{" "}
        <button
          type="button"
          className="link-button"
          onClick={() => download("people-template.csv", TEMPLATE)}
        >
          Download a template
        </button>
      </p>
      <div>
        <label htmlFor="people-file">CSV file</label>
        <input
          id="people-file"
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => choose(e.target.files?.[0] ?? null)}
        />
      </div>
      {error && <p role="alert">{error}</p>}
      <div className="import-actions">
        <button onClick={showPreview} disabled={!file || preview.isPending}>
          {preview.isPending ? "Reading..." : "Preview"}
        </button>
        <button type="button" onClick={close}>
          Cancel
        </button>
      </div>

      {previewed && (
        <>
          <PreviewTable preview={previewed} />
          <MissingFromFile people={previewed.missing_from_file} />
          <div className="import-actions">
            <button
              onClick={runImport}
              disabled={changes === 0 || importer.isPending}
            >
              {importer.isPending
                ? "Importing..."
                : `Add ${previewed.create} and update ${previewed.update}`}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
