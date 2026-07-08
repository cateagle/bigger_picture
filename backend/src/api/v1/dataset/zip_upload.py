import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from src import config
from src.api.deps import require_current_user
from src.db import get_db
from src.models.dataset import DatasetImportCounts, DatasetImportResponse
from src.services.assets import move_asset, resolve_asset_path
from src.services.dataset_import import DatasetImportError, run_import

router = APIRouter()


def _extract_zip_safely(zip_path: Path, dest_dir: Path) -> None:
    """Extract `zip_path` into `dest_dir`, rejecting zip-slip entries.

    Reuses `resolve_asset_path`'s traversal/absolute-path/symlink-escape
    defenses against `dest_dir` instead of `ASSETS_DIR`.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise DatasetImportError("<zip>", None, f"not a valid zip file: {exc}") from exc
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            try:
                target = resolve_asset_path(info.filename, base_dir=dest_dir)
            except ValueError as exc:
                raise DatasetImportError(
                    "<zip>", None, f"unsafe path in zip: {info.filename!r} ({exc})"
                ) from exc
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


@router.post(
    "/zip-upload",
    response_model=DatasetImportResponse,
    status_code=201,
    summary="Bulk Import Dataset From Zip",
    description="""
Upload a zip archive containing up to 7 optional, semicolon-delimited CSVs (labels.csv, cameras.csv, regions.csv, dives.csv, images.csv, candidates.csv, pairs.csv) plus an images/ folder, and import them in dependency order. Requires the scientist role.

The whole import is all-or-nothing: any error aborts with nothing persisted and no asset files left behind. On success, returns per-entity created counts - newly minted uuids (from rows using uuid "new") are never echoed back, so reference such rows by title in later rows of the same import.

Fails with 422 identifying the offending file and row if any CSV row is invalid, references a nonexistent entity, or if the zip is malformed or contains an unsafe path.
""",
)
def zip_upload(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = require_current_user(request)

    job_id = uuid4()
    work_dir = Path(config.IMPORT_DIR) / str(job_id)
    work_dir.mkdir(parents=True)
    pending_moves: list[tuple[Path, Path]] = []

    try:
        zip_path = work_dir / "upload.zip"
        with open(zip_path, "wb") as out:
            shutil.copyfileobj(file.file, out)

        extract_dir = work_dir / "extracted"
        _extract_zip_safely(zip_path, extract_dir)

        summary, pending_moves = run_import(db, extract_dir, user.id)
        db.commit()
    except DatasetImportError as exc:
        db.rollback()
        for temp_path, _ in pending_moves:
            temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail={"file": exc.file, "row": exc.row, "reason": exc.reason},
        )
    except Exception:
        db.rollback()
        for temp_path, _ in pending_moves:
            temp_path.unlink(missing_ok=True)
        raise
    else:
        for temp_path, final_dest in pending_moves:
            move_asset(temp_path, final_dest)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return DatasetImportResponse(
        created=DatasetImportCounts(
            labels=summary.labels,
            cameras=summary.cameras,
            regions=summary.regions,
            dives=summary.dives,
            images=summary.images,
            candidate_pairs=summary.candidate_pairs,
            image_pairs=summary.image_pairs,
        )
    )
