"""Backing up and restoring a SQLite deployment.

    python -m app.backup create [--to DIR] [--keep N]
    python -m app.backup verify ARCHIVE
    python -m app.backup restore ARCHIVE --to DIR

A backup is one .tar.gz holding a consistent copy of the database, every
uploaded file and a manifest of checksums. The database is copied with SQLite's
own online backup, so the API can keep running while it happens, and the copy
is never a half-written file.

What a backup does NOT hold is SECRET_KEY. Stored AI provider keys and
two-step sign-in secrets are encrypted under it, so a restore needs the same
key; keep it somewhere that is not this server. And an archive is not
encrypted: it holds everything the platform does, so store it as carefully as
the server itself.

A restore never writes over anything: it unpacks into a directory that does not
exist yet (or is empty), after checking the archive, and leaves pointing the
app at it to you.
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core import evidence_files

PREFIX = "ai-governance-backup-"
SUFFIX = ".tar.gz"
DATABASE_MEMBER = "database.sqlite3"
MANIFEST_MEMBER = "manifest.json"
EVIDENCE_PREFIX = "evidence/"
FORMAT = 1
# What an uploaded file's stored name looks like: no slashes, no dots at the
# start, nothing that could climb out of the folder it is unpacked into.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$")


class BackupError(Exception):
    """Something a person running this needs to know about, in plain words."""


def sqlite_file(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise BackupError(
            "This backs up SQLite databases. For PostgreSQL use pg_dump (and back up the "
            "uploaded files folder as well)."
        )
    if not url.database or url.database == ":memory:":
        raise BackupError("The database is in memory, so there is nothing on disk to back up.")
    return Path(url.database)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot(database: Path, target: Path) -> None:
    """A consistent copy of a database that may be in use."""
    if not database.is_file():
        raise BackupError(f"There is no database at {database}.")
    source = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True, timeout=30)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def _revision(database: Path) -> str | None:
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None
    except sqlite3.DatabaseError:
        return None
    finally:
        connection.close()


def create_backup(database_url: str, evidence_dir: str | Path, destination: str | Path) -> Path:
    """Writes a new archive into `destination` and returns its path."""
    database = sqlite_file(database_url)
    evidence = Path(evidence_dir)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(UTC)
    name = f"{PREFIX}{stamp:%Y%m%d-%H%M%S}{SUFFIX}"
    final = destination / name
    if final.exists():
        raise BackupError(f"{final} already exists; wait a second and run it again.")
    partial = destination / f".{name}.partial"

    try:
        with tempfile.TemporaryDirectory(dir=destination) as scratch:
            snapshot = Path(scratch) / DATABASE_MEMBER
            _snapshot(database, snapshot)
            files: dict[str, dict] = {
                DATABASE_MEMBER: {"sha256": _sha256(snapshot), "bytes": snapshot.stat().st_size}
            }
            uploads = (
                sorted(p for p in evidence.iterdir() if p.is_file() and not p.is_symlink())
                if evidence.is_dir()
                else []
            )
            # Skip placeholders; everything else is an upload.
            uploads = [p for p in uploads if p.name != ".gitkeep"]
            for upload in uploads:
                files[EVIDENCE_PREFIX + upload.name] = {
                    "sha256": _sha256(upload),
                    "bytes": upload.stat().st_size,
                }
            manifest = {
                "format": FORMAT,
                "created_at": stamp.isoformat(),
                "database_revision": _revision(snapshot),
                "files": files,
            }
            payload = json.dumps(manifest, indent=2).encode()

            with tarfile.open(partial, "w:gz") as archive:
                info = tarfile.TarInfo(MANIFEST_MEMBER)
                info.size = len(payload)
                info.mtime = int(stamp.timestamp())
                archive.addfile(info, io.BytesIO(payload))
                archive.add(snapshot, arcname=DATABASE_MEMBER)
                for upload in uploads:
                    archive.add(upload, arcname=EVIDENCE_PREFIX + upload.name)
        with contextlib.suppress(OSError):
            os.chmod(partial, 0o600)
        os.replace(partial, final)
    finally:
        partial.unlink(missing_ok=True)
    return final


@dataclass
class Report:
    archive: Path
    created_at: str | None = None
    database_revision: str | None = None
    uploads: int = 0
    database_bytes: int = 0
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _read_manifest(archive: tarfile.TarFile) -> dict:
    try:
        member = archive.getmember(MANIFEST_MEMBER)
    except KeyError as error:
        raise BackupError("That is not one of these backups: it has no manifest.") from error
    handle = archive.extractfile(member)
    if handle is None or member.size > 10_000_000:
        raise BackupError("The manifest is unreadable.")
    try:
        manifest = json.loads(handle.read())
    except ValueError as error:
        raise BackupError("The manifest is unreadable.") from error
    if manifest.get("format") != FORMAT or not isinstance(manifest.get("files"), dict):
        raise BackupError("That backup was made in a format this version does not understand.")
    return manifest


def _check_name(name: str) -> None:
    """Only the names this tool writes are ever unpacked, so an archive cannot
    place a file anywhere else."""
    if name == DATABASE_MEMBER:
        return
    if name.startswith(EVIDENCE_PREFIX) and _SAFE_NAME.match(name[len(EVIDENCE_PREFIX) :]):
        return
    raise BackupError(f"The archive lists a file it should not have: {name!r}.")


def _open(path: Path) -> tarfile.TarFile:
    try:
        return tarfile.open(path, "r:gz")
    except (OSError, tarfile.TarError) as error:
        raise BackupError(f"{path} could not be read as a backup: {error}") from error


def verify_backup(path: str | Path) -> Report:
    """Checks that an archive is complete and the database inside it is sound.
    Never changes anything."""
    path = Path(path)
    report = Report(archive=path)
    with _open(path) as archive:
        manifest = _read_manifest(archive)
        report.created_at = manifest.get("created_at")
        report.database_revision = manifest.get("database_revision")
        listed: dict[str, dict] = manifest["files"]
        for name in listed:
            _check_name(name)
        if DATABASE_MEMBER not in listed:
            raise BackupError("The archive has no database in it.")

        members = {m.name: m for m in archive.getmembers() if m.isfile()}
        for name in members:
            if name != MANIFEST_MEMBER and name not in listed:
                report.problems.append(f"{name} is in the archive but not in its manifest.")
        report.uploads = sum(1 for n in listed if n.startswith(EVIDENCE_PREFIX))

        with tempfile.TemporaryDirectory() as scratch:
            for name, expected in listed.items():
                member = members.get(name)
                if member is None:
                    report.problems.append(f"{name} is listed but missing from the archive.")
                    continue
                handle = archive.extractfile(member)
                digest = hashlib.sha256()
                kept = Path(scratch) / DATABASE_MEMBER if name == DATABASE_MEMBER else None
                sink = kept.open("wb") if kept else None
                try:
                    for block in iter(lambda h=handle: h.read(1 << 20), b""):
                        digest.update(block)
                        if sink:
                            sink.write(block)
                finally:
                    if sink:
                        sink.close()
                if digest.hexdigest() != expected.get("sha256"):
                    report.problems.append(f"{name} does not match its checksum.")
            database = Path(scratch) / DATABASE_MEMBER
            if database.is_file():
                report.database_bytes = database.stat().st_size
                _check_database(database, listed, report)
    return report


def _check_database(database: Path, listed: dict, report: Report) -> None:
    try:
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    except sqlite3.DatabaseError as error:
        report.problems.append(f"The database will not open: {error}")
        return
    try:
        result = connection.execute("PRAGMA integrity_check").fetchall()
        if result != [("ok",)]:
            report.problems.append("The database failed SQLite's integrity check.")
            return
        if report.database_revision is None:
            report.problems.append("The database has no migration version recorded.")
        try:
            rows = connection.execute("SELECT storage_path FROM evidence").fetchall()
        except sqlite3.DatabaseError:
            rows = []
        missing = [
            r[0]
            for r in rows
            if evidence_files.stored_name(r[0]) not in {n[len(EVIDENCE_PREFIX) :] for n in listed}
        ]
        if missing:
            report.warnings.append(
                f"{len(missing)} uploaded file(s) the database refers to are not in this backup "
                "(deleted or lost before it was taken)."
            )
    except sqlite3.DatabaseError as error:
        report.problems.append(f"The database could not be read: {error}")
    finally:
        connection.close()


def restore_backup(path: str | Path, target: str | Path) -> tuple[Path, Path]:
    """Unpacks into `target`, which must not hold anything yet. Returns the
    database file and the uploads folder."""
    path, target = Path(path), Path(target)
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise BackupError(
            f"{target} already exists and is not empty. Restore into a new folder; "
            "nothing is ever written over existing data."
        )
    report = verify_backup(path)
    if not report.ok:
        raise BackupError("That backup did not pass its checks: " + "; ".join(report.problems))

    target.mkdir(parents=True, exist_ok=True)
    database = target / "ai_governance.db"
    uploads = target / "evidence"
    uploads.mkdir()
    with _open(path) as archive:
        manifest = _read_manifest(archive)
        for name in manifest["files"]:
            _check_name(name)
            handle = archive.extractfile(archive.getmember(name))
            if handle is None:
                raise BackupError(f"{name} could not be read.")
            destination = (
                database if name == DATABASE_MEMBER else uploads / name[len(EVIDENCE_PREFIX) :]
            )
            with destination.open("wb") as out:
                for block in iter(lambda h=handle: h.read(1 << 20), b""):
                    out.write(block)
    return database, uploads


def backups_in(directory: str | Path) -> list[Path]:
    """This tool's archives in a folder, oldest first."""
    folder = Path(directory)
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir() if p.name.startswith(PREFIX) and p.name.endswith(SUFFIX)
    )


def prune(directory: str | Path, keep: int) -> list[Path]:
    """Deletes all but the newest `keep` archives. Returns what it deleted."""
    if keep < 1:
        raise BackupError("Keep at least one backup.")
    doomed = backups_in(directory)[:-keep]
    for archive in doomed:
        archive.unlink()
    return doomed


def _settings() -> tuple[str, str]:
    from app.core.config import get_settings

    settings = get_settings()
    return settings.database_url, settings.evidence_storage_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.backup", description=__doc__.split("\n")[0]
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Make a new backup.")
    create.add_argument(
        "--to", default="./backups", help="Folder to write it into (default ./backups)."
    )
    create.add_argument(
        "--keep", type=int, help="Afterwards, keep only this many of the newest backups."
    )

    check = commands.add_parser("verify", help="Check a backup without changing anything.")
    check.add_argument("archive")

    restore = commands.add_parser("restore", help="Unpack a backup into a new folder.")
    restore.add_argument("archive")
    restore.add_argument(
        "--to", required=True, help="A folder that does not exist yet (or is empty)."
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            url, evidence = _settings()
            made = create_backup(url, evidence, args.to)
            report = verify_backup(made)
            print(
                f"Wrote {made} ({made.stat().st_size:,} bytes, {report.uploads} uploaded file(s))."
            )
            if not report.ok:
                print(
                    "The new backup FAILED its own check:",
                    *report.problems,
                    sep="\n  ",
                    file=sys.stderr,
                )
                return 1
            if args.keep is not None:
                for gone in prune(args.to, args.keep):
                    print(f"Removed old backup {gone.name}")
            return 0
        if args.command == "verify":
            report = verify_backup(args.archive)
            print(
                f"{report.archive.name}: made {report.created_at}, database version "
                f"{report.database_revision}, {report.uploads} uploaded file(s)."
            )
            for warning in report.warnings:
                print(f"Warning: {warning}")
            if report.ok:
                print("OK: every file matches its checksum and the database is sound.")
                return 0
            print("FAILED:", *report.problems, sep="\n  ", file=sys.stderr)
            return 1
        database, uploads = restore_backup(args.archive, args.to)
        print(
            f"Restored.\n  Database: {database}\n  Uploads:  {uploads}\n\n"
            "To run on it, start the app with:\n"
            f"  DATABASE_URL=sqlite:///{database.resolve().as_posix()}\n"
            f"  EVIDENCE_STORAGE_DIR={uploads.resolve().as_posix()}\n"
            "and the same SECRET_KEY as the original, then run `alembic upgrade head`."
        )
        return 0
    except BackupError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
