import re
import shutil
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import Engine

from src.models.backups import BackupInfo
from src.services.assets import move_asset, resolve_asset_path

_FILENAME_RE = re.compile(r"^db_backup_(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:-\d+)?\.zip$")

_DB_ARCNAME = "app.db"
_AUTH_DB_ARCNAME = "auth.db"


def _vacuum_into(engine: Engine, dest_path: Path) -> None:
    """Snapshot the live database into `dest_path` via SQLite's `VACUUM INTO`.

    Uses `engine.raw_connection()` rather than a SQLAlchemy `Session`/`Connection`:
    SQLAlchemy autobegins a transaction on first `execute()`, and SQLite
    rejects `VACUUM INTO` while a transaction is open on the connection.
    `raw_connection()` hands back a fresh pooled DBAPI connection with no
    transaction open - Python's `sqlite3` module only auto-issues an
    implicit `BEGIN` ahead of INSERT/UPDATE/DELETE, never for VACUUM - so
    running `VACUUM INTO` as the first statement on this connection is safe.
    Verified against this app's actual `make_engine()` setup. `dest_path`
    must not already exist.
    """
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("VACUUM INTO ?", (str(dest_path),))
        raw.commit()
    finally:
        raw.close()


def _vacuum_sqlite_file_into(source_path: str, dest_path: Path) -> None:
    """Snapshot the sqlite file at `source_path` into `dest_path` via `VACUUM INTO`.

    Unlike `_vacuum_into`, this takes a bare file path rather than a
    SQLAlchemy `Engine` - used for the password_auth database, which (by
    design, see src/password_auth/store.py) has no engine on `app.state` to
    reuse. A plain `sqlite3.connect()` has no transaction open yet (Python's
    `sqlite3` only auto-begins one ahead of INSERT/UPDATE/DELETE), so running
    `VACUUM INTO` as the first statement is safe here too.
    """
    conn = sqlite3.connect(source_path)
    try:
        conn.execute("VACUUM INTO ?", (str(dest_path),))
        conn.commit()
    finally:
        conn.close()


def generate_backup_filename(backup_dir: Path) -> str:
    """Return a fresh `db_backup_<UTC timestamp>.zip` filename, not already
    present in `backup_dir`. Appends `-2`, `-3`, ... on the rare same-second
    collision (e.g. two rapid admin clicks).
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    base = f"db_backup_{timestamp}"
    candidate = f"{base}.zip"
    suffix = 2
    while (backup_dir / candidate).exists():
        candidate = f"{base}-{suffix}.zip"
        suffix += 1
    return candidate


def parse_backup_timestamp(filename: str) -> datetime | None:
    match = _FILENAME_RE.match(filename)
    if match is None:
        return None
    return datetime.fromisoformat(match.group(1)).replace(tzinfo=timezone.utc)


def create_backup(engine: Engine, backup_dir: Path, auth_database_path: str) -> BackupInfo:
    """Snapshot the live database (and the password_auth database, if it
    exists) via `VACUUM INTO`, zip them together, and move the zip into
    `backup_dir` under a fresh timestamped name.

    `auth_database_path` is only included if it already exists on disk - a
    deployment where no scientist/admin has ever set a password has no
    password_auth file to speak of, and a backup shouldn't conjure one into
    existence as a side effect.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = backup_dir / ".tmp" / uuid4().hex
    staging_dir.mkdir(parents=True)
    try:
        db_tmp = staging_dir / _DB_ARCNAME
        _vacuum_into(engine, db_tmp)

        auth_db_tmp = staging_dir / _AUTH_DB_ARCNAME
        auth_db_exists = Path(auth_database_path).is_file()
        if auth_db_exists:
            _vacuum_sqlite_file_into(auth_database_path, auth_db_tmp)

        zip_tmp = staging_dir / "backup.zip"
        with zipfile.ZipFile(zip_tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(db_tmp, arcname=_DB_ARCNAME)
            if auth_db_exists:
                zf.write(auth_db_tmp, arcname=_AUTH_DB_ARCNAME)

        filename = generate_backup_filename(backup_dir)
        final_path = backup_dir / filename
        move_asset(zip_tmp, final_path)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    return BackupInfo(
        filename=filename,
        size_bytes=final_path.stat().st_size,
        created_at=parse_backup_timestamp(filename),
    )


def list_backups(backup_dir: Path) -> list[BackupInfo]:
    """List every regular file in `backup_dir`, newest-first by filename.

    Lists any regular file (not just ones matching the naming pattern) so a
    backup added out-of-band (e.g. `docker cp`) is still visible, with
    `created_at=None` if its name doesn't parse. The `.tmp` staging
    directory is skipped because it isn't a regular file.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    infos = []
    for entry in backup_dir.iterdir():
        if not entry.is_file():
            continue
        infos.append(
            BackupInfo(
                filename=entry.name,
                size_bytes=entry.stat().st_size,
                created_at=parse_backup_timestamp(entry.name),
            )
        )
    infos.sort(key=lambda info: info.filename, reverse=True)
    return infos


def resolve_backup_file(backup_dir: Path, filename: str) -> Path:
    """Resolve `filename` to an existing file within `backup_dir`.

    Raises `ValueError` (unsafe filename, e.g. traversal) or
    `FileNotFoundError` (safe filename but no such file) - callers should
    map both to a generic 404, per `resolve_asset_path`'s own
    defense-in-depth reasoning against leaking which case applies.
    """
    path = resolve_asset_path(filename, base_dir=backup_dir)
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path
