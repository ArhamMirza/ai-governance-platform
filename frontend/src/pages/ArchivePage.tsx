import { ArchiveTable } from "../features/ai-systems/components/ArchiveTable";

export function ArchivePage() {
  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Archive</h1>
          <p>
            Retired AI systems. Everything recorded about them is kept read-only until the
            retention period set at retirement runs out, and only then can it be deleted.
          </p>
        </div>
      </div>

      <ArchiveTable />
    </section>
  );
}
