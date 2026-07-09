import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from src import config
from src.models.backups import BackupInfo, BackupListResponse
from src.services.backups import (
    create_backup,
    generate_backup_filename,
    list_backups,
    parse_backup_timestamp,
    resolve_backup_file,
)
from src.services.assets import move_asset

router = APIRouter()


def _backup_dir() -> Path:
    # Read at call time, not bound at import time, so tests that monkeypatch
    # config.BACKUP_DIR (see resolve_asset_path's own base_dir default for
    # the same reasoning) keep working.
    return Path(config.BACKUP_DIR)


def _resolve_or_404(filename: str) -> Path:
    try:
        return resolve_backup_file(_backup_dir(), filename)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Backup not found")


@router.post(
    "/create",
    response_model=BackupInfo,
    status_code=201,
    summary="Create Backup",
    description="""
Snapshot the live database via SQLite's VACUUM INTO, zip it, and move it into the backup directory. Requires the admin role.

The resulting zip contains a single file, app.db, which is a complete and consistent snapshot of the database at the moment the backup was taken - safe to run against the live database with no downtime.
""",
)
def create_backup_endpoint(request: Request):
    return create_backup(request.app.state.engine, _backup_dir())


@router.get(
    "",
    response_model=BackupListResponse,
    summary="List Backups",
    description="""
List every file in the backup directory, newest first. Requires the admin role.

Includes files that weren't created through this API (e.g. copied in by hand) - those are still listed, with created_at set to null since their filename doesn't encode a timestamp.
""",
)
def list_backups_endpoint():
    return BackupListResponse(backups=list_backups(_backup_dir()))


@router.get(
    "/{filename}/download",
    summary="Download Backup",
    description="""
Download a backup zip by filename. Requires the admin role.

Fails with 404 if the filename doesn't resolve to an existing file in the backup directory.
""",
)
def download_backup_endpoint(filename: str):
    path = _resolve_or_404(filename)
    return FileResponse(path, media_type="application/zip", filename=filename)


@router.post(
    "/{filename}/delete",
    status_code=204,
    summary="Delete Backup",
    description="""
Delete a backup zip by filename. Requires the admin role.

Fails with 404 if the filename doesn't resolve to an existing file in the backup directory.
""",
)
def delete_backup_endpoint(filename: str):
    path = _resolve_or_404(filename)
    path.unlink()


@router.post(
    "/upload",
    response_model=BackupInfo,
    status_code=201,
    summary="Upload Backup",
    description="""
Upload a backup zip archive, e.g. one previously downloaded from this API. Requires the admin role.

The uploaded file's own name is ignored - it is stored under a fresh server-generated db_backup_<timestamp>.zip name, alongside locally-created backups. Only checked for being a structurally valid zip archive; its contents are not validated here.

Fails with 422 if the uploaded file is not a valid zip archive.
""",
)
def upload_backup_endpoint(file: UploadFile = File(...)):
    backup_dir = _backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = backup_dir / ".tmp" / uuid4().hex
    staging_dir.mkdir(parents=True)
    try:
        staged_zip = staging_dir / "upload.zip"
        with open(staged_zip, "wb") as out:
            shutil.copyfileobj(file.file, out)

        if not zipfile.is_zipfile(staged_zip):
            raise HTTPException(status_code=422, detail="Uploaded file is not a valid zip archive")

        filename = generate_backup_filename(backup_dir)
        final_path = backup_dir / filename
        move_asset(staged_zip, final_path)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    return BackupInfo(
        filename=filename,
        size_bytes=final_path.stat().st_size,
        created_at=parse_backup_timestamp(filename),
    )
