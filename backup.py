"""Portable Work Log backups with an independent SQLite snapshot."""

from contextlib import closing
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
from tempfile import mkdtemp, mkstemp, TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


_DATABASE = "worklog.db"
_MANIFEST = "manifest.json"
_FORMAT = "terraanalytica-worklog-backup-v1"
_ATTACHMENT = re.compile(r"attachments/\d+/\d+(\.[a-zA-Z0-9]{1,16})?")


def _attachment_rows(database):
    return database.execute(
        """SELECT a.id, a.filename, a.file_path, a.blob_data IS NOT NULL, e.project_id
           FROM attachments a JOIN entries e ON e.id = a.entry_id ORDER BY a.id"""
    ).fetchall()


def _write_backup(database_path, snapshot, archive):
    uri = database_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as source:
        with closing(sqlite3.connect(snapshot)) as copied:
            source.backup(copied)
            missing = 0
            for attachment_id, filename, file_path, has_blob, project_id in _attachment_rows(copied):
                if not file_path:
                    missing += not has_blob
                    continue

                original = Path(file_path)
                if not original.is_absolute():
                    original = database_path.parent / original
                if not original.is_file() and Path(filename).name == filename:
                    original = database_path.parent / "attachments" / str(project_id) / filename

                member = None
                if original.is_file():
                    suffix = Path(filename).suffix
                    if not re.fullmatch(r"\.[a-zA-Z0-9]{1,16}", suffix):
                        suffix = ""
                    member = f"attachments/{project_id}/{attachment_id}{suffix}"
                    archive.write(original, member)
                elif not has_blob:
                    missing += 1
                copied.execute("UPDATE attachments SET file_path = ? WHERE id = ?", (member, attachment_id))
            copied.commit()
    archive.write(snapshot, _DATABASE)
    archive.writestr(_MANIFEST, json.dumps({"format": _FORMAT, "missingAttachments": missing}))
    return missing


def create_backup(database_path, destination):
    """Write a backup ZIP and return the number of attachments without available data."""
    database_path = Path(database_path)
    destination = Path(destination)
    if destination.resolve() == database_path.resolve():
        raise ValueError("Choose a ZIP path different from the active database.")

    descriptor, pending = mkstemp(prefix=".worklog-backup-", dir=destination.parent)
    os.close(descriptor)
    try:
        with TemporaryDirectory() as temporary, ZipFile(pending, "w", ZIP_DEFLATED) as archive:
            missing = _write_backup(database_path, Path(temporary) / _DATABASE, archive)
        os.replace(pending, destination)
        return missing
    finally:
        Path(pending).unlink(missing_ok=True)


def _copy_member(archive, member, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(member) as source, destination.open("xb") as output:
        shutil.copyfileobj(source, output)


def restore_backup(backup_path, parent_directory):
    """Restore a validated ZIP into a new directory, then return its database path."""
    restored = Path(mkdtemp(prefix="Work Log restore ", dir=parent_directory)).resolve()
    database_path = restored / _DATABASE
    try:
        with ZipFile(backup_path) as archive:
            names = archive.namelist()
            members = set(names)
            if len(names) != len(members) or not {_DATABASE, _MANIFEST} <= members:
                raise ValueError("This ZIP is missing the Work Log backup files or contains duplicates.")
            if archive.getinfo(_MANIFEST).file_size > 4096:
                raise ValueError("The Work Log backup manifest is too large.")
            if json.loads(archive.read(_MANIFEST)).get("format") != _FORMAT:
                raise ValueError("This Work Log backup format is not supported.")
            _copy_member(archive, _DATABASE, database_path)
            with closing(sqlite3.connect(database_path)) as database:
                database.execute("PRAGMA trusted_schema = OFF")
                if database.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                    raise ValueError("The backup database failed its integrity check.")
                if database.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise ValueError("The backup database contains broken links.")
                expected = {_DATABASE, _MANIFEST}
                for attachment_id, _, member, _, project_id in _attachment_rows(database):
                    if member is None:
                        continue
                    if (
                        not _ATTACHMENT.fullmatch(member)
                        or member.split(".", 1)[0] != f"attachments/{project_id}/{attachment_id}"
                        or member in expected
                        or member not in members
                    ):
                        raise ValueError("The backup contains an invalid or missing attachment.")
                    expected.add(member)
                    target = restored / member
                    _copy_member(archive, member, target)
                    database.execute("UPDATE attachments SET file_path = ? WHERE id = ?", (str(target), attachment_id))
                if members != expected:
                    raise ValueError("The backup contains unexpected files.")
                database.commit()
        return database_path
    except Exception:
        shutil.rmtree(restored, ignore_errors=True)
        raise
