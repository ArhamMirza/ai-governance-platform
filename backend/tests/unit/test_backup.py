"""Backing up and restoring a SQLite deployment: the archive is complete, a
restore reproduces the data, and a damaged or hostile archive is caught.
Real files and real SQLite throughout; nothing here is mocked."""

import io
import json
import sqlite3
import tarfile
from pathlib import Path

import pytest

from app import backup
from app.backup import BackupError
from app.core import evidence_files, vector_store


@pytest.fixture()
def deployment(tmp_path: Path):
    """A database with a few rows and two uploaded files, as a server would hold."""
    database = tmp_path / "live" / "ai_governance.db"
    database.parent.mkdir()
    uploads = tmp_path / "live" / "evidence"
    uploads.mkdir()
    (uploads / ".gitkeep").write_bytes(b"")
    (uploads / "aaaa1111.pdf").write_bytes(b"%PDF first")
    (uploads / "bbbb2222.txt").write_bytes(b"second upload")
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE alembic_version (version_num TEXT NOT NULL);
        INSERT INTO alembic_version VALUES ('abc123');
        CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);
        INSERT INTO users (email) VALUES ('ada@example.com'), ('bob@example.com');
        CREATE TABLE evidence (id INTEGER PRIMARY KEY, storage_path TEXT);
        INSERT INTO evidence (storage_path) VALUES
            ('./storage/evidence/aaaa1111.pdf'), ('C:\\old\\place\\bbbb2222.txt');
        """
    )
    connection.commit()
    connection.close()
    return {
        "url": f"sqlite:///{database.as_posix()}",
        "database": database,
        "uploads": uploads,
        "backups": tmp_path / "backups",
        "root": tmp_path,
    }


def make(deployment) -> Path:
    return backup.create_backup(deployment["url"], deployment["uploads"], deployment["backups"])


def rewrite(archive: Path, change) -> Path:
    """A copy of an archive with its members altered by `change(members)`."""
    with tarfile.open(archive) as source:
        members = {m.name: source.extractfile(m).read() for m in source.getmembers() if m.isfile()}
    change(members)
    damaged = archive.with_name("damaged.tar.gz")
    with tarfile.open(damaged, "w:gz") as out:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            out.addfile(info, io.BytesIO(data))
    return damaged


# ---------- making one ----------


def test_a_backup_holds_the_database_every_upload_and_a_manifest(deployment) -> None:
    archive = make(deployment)

    assert archive.name.startswith("ai-governance-backup-") and archive.suffix == ".gz"
    with tarfile.open(archive) as tar:
        names = sorted(m.name for m in tar.getmembers())
        manifest = json.loads(tar.extractfile("manifest.json").read())
    assert names == [
        "database.sqlite3",
        "evidence/aaaa1111.pdf",
        "evidence/bbbb2222.txt",
        "manifest.json",
    ]
    assert manifest["database_revision"] == "abc123"
    assert set(manifest["files"]) == {n for n in names if n != "manifest.json"}


def test_a_backup_does_not_disturb_the_live_data(deployment) -> None:
    before = deployment["database"].read_bytes()

    make(deployment)

    assert deployment["database"].read_bytes() == before
    assert sorted(p.name for p in deployment["uploads"].iterdir()) == [
        ".gitkeep",
        "aaaa1111.pdf",
        "bbbb2222.txt",
    ]
    # Nothing half-written is left lying in the backups folder.
    assert [p.name for p in deployment["backups"].iterdir() if p.name.startswith(".")] == []


def test_a_backup_taken_while_someone_is_writing_holds_only_what_was_committed(
    deployment,
) -> None:
    writer = sqlite3.connect(deployment["database"])
    writer.execute("INSERT INTO users (email) VALUES ('uncommitted@example.com')")

    archive = make(deployment)
    writer.rollback()
    writer.close()

    target = deployment["root"] / "restored"
    database, _ = backup.restore_backup(archive, target)
    emails = [r[0] for r in sqlite3.connect(database).execute("SELECT email FROM users")]
    assert emails == ["ada@example.com", "bob@example.com"]


def test_the_search_index_comes_along_too(deployment) -> None:
    if not vector_store.vectors_available():
        pytest.skip("sqlite-vec is not available on this machine")
    import sqlite_vec

    connection = sqlite3.connect(deployment["database"])
    vector_store._load_into(connection)
    connection.execute("CREATE VIRTUAL TABLE chunk_vectors USING vec0(embedding float[3])")
    connection.execute(
        "INSERT INTO chunk_vectors (rowid, embedding) VALUES (1, ?)",
        [sqlite_vec.serialize_float32([1.0, 2.0, 3.0])],
    )
    connection.commit()
    connection.close()

    database, _ = backup.restore_backup(make(deployment), deployment["root"] / "restored")

    restored = sqlite3.connect(database)
    vector_store._load_into(restored)
    assert restored.execute("SELECT count(*) FROM chunk_vectors").fetchone() == (1,)


# ---------- checking one ----------


def test_a_good_backup_passes_and_says_what_is_in_it(deployment) -> None:
    report = backup.verify_backup(make(deployment))

    assert report.ok and report.problems == []
    assert (report.uploads, report.database_revision) == (2, "abc123")
    assert report.database_bytes > 0
    assert report.warnings == []


def test_a_file_that_changed_after_the_backup_is_caught(deployment) -> None:
    archive = make(deployment)
    damaged = rewrite(archive, lambda m: m.update({"evidence/aaaa1111.pdf": b"tampered"}))

    report = backup.verify_backup(damaged)

    assert not report.ok
    assert any("aaaa1111.pdf" in p and "checksum" in p for p in report.problems)


def test_a_database_that_changed_after_the_backup_is_caught(deployment) -> None:
    damaged = rewrite(make(deployment), lambda m: m.update({"database.sqlite3": b"not a database"}))

    assert not backup.verify_backup(damaged).ok


def test_a_missing_file_and_an_extra_file_are_both_caught(deployment) -> None:
    archive = make(deployment)

    missing = backup.verify_backup(rewrite(archive, lambda m: m.pop("evidence/bbbb2222.txt")))
    extra = backup.verify_backup(rewrite(archive, lambda m: m.update({"evidence/cccc.txt": b"x"})))

    assert any("missing" in p for p in missing.problems)
    assert any("not in its manifest" in p for p in extra.problems)


def test_a_database_with_a_failed_integrity_check_is_caught(deployment, tmp_path: Path) -> None:
    # Damage a real page, then make the manifest agree with the damaged bytes, so
    # only SQLite's own check can notice.
    archive = make(deployment)
    import hashlib

    def corrupt(members: dict) -> None:
        data = bytearray(members["database.sqlite3"])
        for offset in range(len(data) // 2, len(data), 97):
            data[offset] = 0xFF
        members["database.sqlite3"] = bytes(data)
        manifest = json.loads(members["manifest.json"])
        manifest["files"]["database.sqlite3"]["sha256"] = hashlib.sha256(data).hexdigest()
        members["manifest.json"] = json.dumps(manifest).encode()

    report = backup.verify_backup(rewrite(archive, corrupt))

    assert not report.ok


def test_an_upload_the_database_needs_but_the_backup_lacks_is_a_warning(deployment) -> None:
    (deployment["uploads"] / "bbbb2222.txt").unlink()

    report = backup.verify_backup(make(deployment))

    assert report.ok
    assert any("1 uploaded file" in w for w in report.warnings)


@pytest.mark.parametrize(
    "build",
    [
        lambda m: m.pop("manifest.json"),
        lambda m: m.update({"manifest.json": b"{not json"}),
        lambda m: m.update({"manifest.json": b'{"format": 99, "files": {}}'}),
    ],
)
def test_something_that_is_not_one_of_these_backups_is_refused(deployment, build) -> None:
    damaged = rewrite(make(deployment), build)

    with pytest.raises(BackupError):
        backup.verify_backup(damaged)


def test_a_file_that_is_not_an_archive_is_refused(tmp_path: Path) -> None:
    junk = tmp_path / "junk.tar.gz"
    junk.write_bytes(b"this is not a tar file")

    with pytest.raises(BackupError, match="could not be read"):
        backup.verify_backup(junk)


@pytest.mark.parametrize("name", ["evidence/../escape.txt", "evidence/sub/dir.txt", "etc/passwd"])
def test_an_archive_cannot_name_a_file_outside_the_folder(deployment, name: str) -> None:
    def hostile(members: dict) -> None:
        manifest = json.loads(members["manifest.json"])
        manifest["files"][name] = {"sha256": "0" * 64, "bytes": 1}
        members["manifest.json"] = json.dumps(manifest).encode()
        members[name] = b"x"

    with pytest.raises(BackupError, match="should not have"):
        backup.verify_backup(rewrite(make(deployment), hostile))


# ---------- restoring one ----------


def test_a_restore_reproduces_the_data_and_the_files(deployment) -> None:
    target = deployment["root"] / "restored"

    database, uploads = backup.restore_backup(make(deployment), target)

    assert database == target / "ai_governance.db" and uploads == target / "evidence"
    restored = sqlite3.connect(database)
    assert restored.execute("SELECT count(*) FROM users").fetchone() == (2,)
    assert restored.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
    assert (uploads / "aaaa1111.pdf").read_bytes() == b"%PDF first"
    assert (uploads / "bbbb2222.txt").read_bytes() == b"second upload"


def test_a_restore_never_writes_over_existing_data(deployment) -> None:
    archive = make(deployment)
    occupied = deployment["root"] / "occupied"
    occupied.mkdir()
    (occupied / "precious.txt").write_text("keep me")

    with pytest.raises(BackupError, match="not empty"):
        backup.restore_backup(archive, occupied)
    with pytest.raises(BackupError, match="not empty"):
        backup.restore_backup(archive, deployment["uploads"].parent)

    assert (occupied / "precious.txt").read_text() == "keep me"
    assert backup.restore_backup(archive, deployment["root"] / "empty-is-fine")


def test_a_restore_into_an_empty_existing_folder_is_allowed(deployment) -> None:
    empty = deployment["root"] / "empty"
    empty.mkdir()

    database, _ = backup.restore_backup(make(deployment), empty)

    assert database.is_file()


def test_a_backup_that_fails_its_checks_is_not_restored(deployment) -> None:
    damaged = rewrite(make(deployment), lambda m: m.update({"evidence/aaaa1111.pdf": b"bad"}))
    target = deployment["root"] / "restored"

    with pytest.raises(BackupError, match="did not pass"):
        backup.restore_backup(damaged, target)

    assert not target.exists()


def test_uploads_are_found_again_wherever_the_folder_now_is(deployment, monkeypatch) -> None:
    """The database may remember a file as './storage/evidence/x.pdf' or as a
    Windows path; after a restore into another folder both must still resolve."""
    _, uploads = backup.restore_backup(make(deployment), deployment["root"] / "restored")
    monkeypatch.setattr(
        evidence_files,
        "get_settings",
        lambda: type("S", (), {"evidence_storage_dir": str(uploads)}),
    )
    restored = sqlite3.connect(deployment["root"] / "restored" / "ai_governance.db")

    for (recorded,) in restored.execute("SELECT storage_path FROM evidence"):
        assert evidence_files.path_for(recorded).is_file(), recorded


@pytest.mark.parametrize(
    ("recorded", "name"),
    [
        ("./storage/evidence/a.pdf", "a.pdf"),
        ("/srv/app/evidence/a.pdf", "a.pdf"),
        ("C:\\Users\\me\\evidence\\a.pdf", "a.pdf"),
        ("a.pdf", "a.pdf"),
    ],
)
def test_a_recorded_path_is_reduced_to_the_stored_name(recorded: str, name: str) -> None:
    assert evidence_files.stored_name(recorded) == name


# ---------- keeping a few ----------


def test_prune_keeps_the_newest_and_ignores_anything_else(tmp_path: Path) -> None:
    for stamp in ("20260101-000000", "20260102-000000", "20260103-000000"):
        (tmp_path / f"ai-governance-backup-{stamp}.tar.gz").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("not a backup")
    (tmp_path / "other-20250101.tar.gz").write_bytes(b"x")

    gone = backup.prune(tmp_path, keep=2)

    assert [p.name for p in gone] == ["ai-governance-backup-20260101-000000.tar.gz"]
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "ai-governance-backup-20260102-000000.tar.gz",
        "ai-governance-backup-20260103-000000.tar.gz",
        "notes.txt",
        "other-20250101.tar.gz",
    ]
    with pytest.raises(BackupError):
        backup.prune(tmp_path, keep=0)


# ---------- what it will not do ----------


def test_only_sqlite_is_backed_up(tmp_path: Path) -> None:
    with pytest.raises(BackupError, match="pg_dump"):
        backup.create_backup("postgresql://u:p@host/db", tmp_path, tmp_path / "out")
    with pytest.raises(BackupError, match="in memory"):
        backup.create_backup("sqlite://", tmp_path, tmp_path / "out")
    with pytest.raises(BackupError, match="no database"):
        backup.create_backup(
            f"sqlite:///{(tmp_path / 'missing.db').as_posix()}", tmp_path, tmp_path / "out"
        )


# ---------- the command line ----------


def test_the_command_line_makes_checks_and_restores_a_backup(
    deployment, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        backup, "_settings", lambda: (deployment["url"], str(deployment["uploads"]))
    )
    out = str(deployment["backups"])

    assert backup.main(["create", "--to", out, "--keep", "5"]) == 0
    archive = backup.backups_in(out)[0]
    assert backup.main(["verify", str(archive)]) == 0
    assert "OK" in capsys.readouterr().out
    target = str(deployment["root"] / "restored")
    assert backup.main(["restore", str(archive), "--to", target]) == 0
    text = capsys.readouterr().out
    assert "DATABASE_URL=sqlite:///" in text and "SECRET_KEY" in text


def test_the_command_line_reports_failure_with_a_nonzero_exit(
    deployment, monkeypatch, capsys
) -> None:
    damaged = rewrite(make(deployment), lambda m: m.update({"evidence/aaaa1111.pdf": b"bad"}))

    assert backup.main(["verify", str(damaged)]) == 1
    assert "FAILED" in capsys.readouterr().err
    assert backup.main(["verify", str(deployment["root"] / "nope.tar.gz")]) == 1
    assert "Error:" in capsys.readouterr().err
    monkeypatch.setattr(backup, "_settings", lambda: ("postgresql://x/y", "."))
    assert backup.main(["create", "--to", str(deployment["backups"])]) == 1
