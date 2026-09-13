"""Index everything that is waiting to be indexed.

    python -m app.cli.index_documents [--limit N]

Two queues, both drained here: documents uploaded before search existed, and
governance records whose text has changed since they were last indexed.

Safe to re-run, and safe to interrupt: each source is indexed and removed
from the queue independently, so a run that stops halfway loses nothing but
the time.
"""

import argparse

from app.core.database import SessionLocal
from app.services import document_index_service


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="Index at most this many of each."
    )
    arguments = parser.parse_args()

    db = SessionLocal()
    try:
        pending = document_index_service.pending_evidence_ids(db)
        if pending:
            print(f"{len(pending)} document(s) pending.")
            for status, count in sorted(
                document_index_service.backfill(db, limit=arguments.limit).items()
            ):
                print(f"  {status:12} {count}")
        else:
            print("No documents pending.")

        depth = document_index_service.queue_depth(db)
        if depth:
            print(f"{depth} record(s) queued for reindexing.")
            for source_type, count in sorted(
                document_index_service.drain(db, limit=arguments.limit).items()
            ):
                print(f"  {source_type:18} {count}")
        else:
            print("No records queued.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
