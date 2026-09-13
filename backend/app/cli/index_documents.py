"""Index evidence that was uploaded before document search existed.

    python -m app.cli.index_documents [--limit N]

Safe to re-run: it only touches evidence still marked pending, and each
document is indexed independently, so a file that cannot be read is recorded
as such and the run carries on.
"""

import argparse

from app.core.database import SessionLocal
from app.services import document_index_service


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="Index at most this many documents."
    )
    arguments = parser.parse_args()

    db = SessionLocal()
    try:
        pending = document_index_service.pending_evidence_ids(db)
        if not pending:
            print("Nothing pending. Every document is already indexed.")
            return
        print(f"{len(pending)} document(s) pending; indexing {arguments.limit or len(pending)}.")
        tally = document_index_service.backfill(db, limit=arguments.limit)
    finally:
        db.close()

    for status, count in sorted(tally.items()):
        print(f"  {status:12} {count}")


if __name__ == "__main__":
    main()
