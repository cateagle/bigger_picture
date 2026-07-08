import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.constants import (
    CANDIDATE_STATUS_INT,
    IMAGE_STATUS_INT,
    PAIR_STATUS_INT,
    CandidateStatus,
    ImageStatus,
    PairStatus,
)
from src.schema.cameras import Camera
from src.schema.dives import Dive
from src.schema.images import Image
from src.schema.regions import Region
from src.services.assets import read_image_dimensions, resolve_asset_path, stage_source_file
from src.services.cameras import create_camera
from src.services.candidate_pairs import create_candidate_pair
from src.services.dives import create_dive, resolve_or_default_camera_id
from src.services.errors import ConflictError, SameDiveError
from src.services.image_pairs import create_image_pair
from src.services.images import create_image
from src.services.labels import create_label
from src.services.lookups import get_by_title, get_by_uuid
from src.services.regions import create_region
from src.util import new_uuid


@dataclass
class DatasetImportError(Exception):
    """A single import failure, pinpointing which file/row caused it.

    `row` is the 1-based CSV row number including the header (so the first
    data row is row 2), or `None` for file-level errors (e.g. a missing
    `images/` folder).
    """

    file: str
    row: int | None
    reason: str

    def __post_init__(self) -> None:
        location = f"{self.file} row {self.row}" if self.row is not None else self.file
        super().__init__(f"{location}: {self.reason}")


@dataclass
class ImportSummary:
    labels: int = 0
    cameras: int = 0
    regions: int = 0
    dives: int = 0
    images: int = 0
    candidate_pairs: int = 0
    image_pairs: int = 0


def _resolve_uuid_field(raw: str | None, *, file: str, row: int) -> UUID:
    raw = (raw or "").strip()
    if raw.lower() == "new":
        return new_uuid()
    try:
        return UUID(raw)
    except ValueError:
        raise DatasetImportError(file, row, f"invalid uuid: {raw!r}")


def _resolve_status(
    raw: str | None, status_map: dict[str, int], default_id: int, *, file: str, row: int
) -> int:
    raw = (raw or "").strip()
    if not raw:
        return default_id
    status_id = status_map.get(raw)
    if status_id is None:
        raise DatasetImportError(file, row, f"unrecognized status: {raw!r}")
    return status_id


def _resolve_metadata(raw: str | None, *, file: str, row: int) -> Any | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        raise DatasetImportError(file, row, f"invalid metadata JSON: {raw!r}")


def _resolve_optional_int(raw: str | None, *, field: str, file: str, row: int) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise DatasetImportError(file, row, f"invalid {field}: {raw!r}")


def _resolve_ref(
    db: Session, model, uuid_raw: str | None, title_raw: str | None, *, file: str, row: int, kind: str
):
    """Resolve a `<kind>_uuid`/`<kind>_title` column pair. uuid takes precedence.

    Returns None if both are empty. Raises `DatasetImportError` if a uuid is
    malformed, or if neither resolves to an existing row.
    """
    uuid_raw = (uuid_raw or "").strip()
    title_raw = (title_raw or "").strip()
    if uuid_raw:
        try:
            uuid_value = UUID(uuid_raw)
        except ValueError:
            raise DatasetImportError(file, row, f"invalid {kind} uuid: {uuid_raw!r}")
        obj = get_by_uuid(db, model, uuid_value.bytes)
    elif title_raw:
        obj = get_by_title(db, model, title_raw)
    else:
        return None
    if obj is None:
        raise DatasetImportError(file, row, f"{kind} not found: {uuid_raw or title_raw!r}")
    return obj


def _import_labels(db: Session, path: Path, creator_id: int) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row_no, row in enumerate(reader, start=2):
            uuid_value = _resolve_uuid_field(row.get("uuid"), file="labels.csv", row=row_no)
            scope = (row.get("scope") or "").strip()
            title = (row.get("title") or "").strip()
            if not scope:
                raise DatasetImportError("labels.csv", row_no, "scope is required")
            if not title:
                raise DatasetImportError("labels.csv", row_no, "title is required")
            try:
                create_label(
                    db,
                    uuid=uuid_value,
                    scope=scope,
                    title=title,
                    description=row.get("description") or None,
                    creator_id=creator_id,
                )
            except ConflictError as exc:
                raise DatasetImportError("labels.csv", row_no, str(exc)) from exc
            count += 1
    return count


def _import_simple_metadata_entity(db: Session, path: Path, filename: str, create_fn, creator_id: int) -> int:
    """Shared row processing for cameras.csv/regions.csv: uuid, title, metadata, description."""
    if not path.exists():
        return 0
    count = 0
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row_no, row in enumerate(reader, start=2):
            uuid_value = _resolve_uuid_field(row.get("uuid"), file=filename, row=row_no)
            title = (row.get("title") or "").strip()
            if not title:
                raise DatasetImportError(filename, row_no, "title is required")
            metadata = _resolve_metadata(row.get("metadata"), file=filename, row=row_no)
            try:
                create_fn(
                    db,
                    uuid=uuid_value,
                    title=title,
                    metadata=metadata,
                    description=row.get("description") or None,
                    creator_id=creator_id,
                )
            except ConflictError as exc:
                raise DatasetImportError(filename, row_no, str(exc)) from exc
            count += 1
    return count


def _import_dives(db: Session, path: Path, creator_id: int) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row_no, row in enumerate(reader, start=2):
            uuid_value = _resolve_uuid_field(row.get("uuid"), file="dives.csv", row=row_no)
            title = (row.get("title") or "").strip()
            if not title:
                raise DatasetImportError("dives.csv", row_no, "title is required")
            metadata = _resolve_metadata(row.get("metadata"), file="dives.csv", row=row_no)

            region = _resolve_ref(
                db, Region, row.get("region_uuid"), row.get("region_title"),
                file="dives.csv", row=row_no, kind="region",
            )
            if region is None:
                raise DatasetImportError(
                    "dives.csv", row_no, "exactly one of region_uuid/region_title must be set"
                )

            camera_uuid_raw = (row.get("camera_uuid") or "").strip()
            camera_title_raw = (row.get("camera_title") or "").strip()
            if camera_uuid_raw or camera_title_raw:
                camera = _resolve_ref(
                    db, Camera, camera_uuid_raw, camera_title_raw,
                    file="dives.csv", row=row_no, kind="camera",
                )
                camera_id = camera.id
            else:
                camera_id = resolve_or_default_camera_id(db, None, creator_id)

            try:
                create_dive(
                    db,
                    uuid=uuid_value,
                    title=title,
                    metadata=metadata,
                    description=row.get("description") or None,
                    region_id=region.id,
                    camera_id=camera_id,
                    creator_id=creator_id,
                )
            except ConflictError as exc:
                raise DatasetImportError("dives.csv", row_no, str(exc)) from exc
            count += 1
    return count


def _import_images(
    db: Session, csv_path: Path, images_root: Path, creator_id: int
) -> tuple[int, list[tuple[Path, Path]]]:
    if not csv_path.exists():
        return 0, []
    if not images_root.is_dir():
        raise DatasetImportError(
            "images.csv", None, "images/ folder is required when images.csv is present"
        )

    pending: list[tuple[Path, Path]] = []
    count = 0
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row_no, row in enumerate(reader, start=2):
            image_uuid = _resolve_uuid_field(row.get("uuid"), file="images.csv", row=row_no)

            dive = _resolve_ref(
                db, Dive, row.get("dive_uuid"), row.get("dive_title"),
                file="images.csv", row=row_no, kind="dive",
            )
            if dive is None:
                raise DatasetImportError(
                    "images.csv", row_no, "exactly one of dive_uuid/dive_title must be set"
                )

            source_path = (row.get("source_path") or "").strip()
            if not source_path:
                raise DatasetImportError("images.csv", row_no, "source_path is required")
            try:
                source_file = resolve_asset_path(source_path, base_dir=images_root)
            except ValueError as exc:
                raise DatasetImportError("images.csv", row_no, f"invalid source_path: {exc}") from exc
            if not source_file.is_file():
                raise DatasetImportError(
                    "images.csv", row_no, f"source file not found: {source_path!r}"
                )

            filename = (row.get("filename") or "").strip() or source_path
            filepath = (row.get("filepath") or "").strip()
            if not filepath:
                extension = Path(source_path).suffix.lstrip(".")
                if not extension:
                    raise DatasetImportError(
                        "images.csv", row_no,
                        "source_path has no extension; filepath must be given explicitly",
                    )
                filepath = f"{UUID(bytes=dive.uuid)}/{image_uuid}.{extension}"

            try:
                final_dest = resolve_asset_path(filepath)
            except ValueError as exc:
                raise DatasetImportError("images.csv", row_no, f"invalid filepath: {exc}") from exc

            # Resolve every remaining field - all of which can fail - before
            # touching the filesystem, so a validation error never leaves a
            # staged temp file that nothing will clean up.
            status_id = _resolve_status(
                row.get("status"), IMAGE_STATUS_INT, IMAGE_STATUS_INT[ImageStatus.HIDDEN],
                file="images.csv", row=row_no,
            )
            metadata = _resolve_metadata(row.get("metadata"), file="images.csv", row=row_no)
            difficulty = _resolve_optional_int(
                row.get("difficulty"), field="difficulty", file="images.csv", row=row_no
            )
            priority = _resolve_optional_int(
                row.get("priority"), field="priority", file="images.csv", row=row_no
            )

            temp_path = stage_source_file(source_file)
            try:
                size_x, size_y = read_image_dimensions(temp_path)
            except ValueError as exc:
                temp_path.unlink(missing_ok=True)
                raise DatasetImportError("images.csv", row_no, f"could not decode image: {exc}") from exc

            try:
                create_image(
                    db,
                    uuid=image_uuid,
                    filename=filename,
                    filepath=filepath,
                    dive_id=dive.id,
                    status_id=status_id,
                    size_x=size_x,
                    size_y=size_y,
                    metadata=metadata,
                    difficulty=difficulty,
                    priority=priority,
                    creator_id=creator_id,
                )
            except ConflictError as exc:
                temp_path.unlink(missing_ok=True)
                raise DatasetImportError("images.csv", row_no, str(exc)) from exc

            pending.append((temp_path, final_dest))
            count += 1
    return count, pending


def _import_pair_csv(
    db: Session, path: Path, filename: str, status_map: dict[str, int], default_status: str, create_fn, creator_id: int
) -> int:
    """Shared row processing for candidates.csv/pairs.csv: image_a, image_b, status."""
    if not path.exists():
        return 0
    count = 0
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row_no, row in enumerate(reader, start=2):
            uuid_a_raw = (row.get("image_a") or "").strip()
            uuid_b_raw = (row.get("image_b") or "").strip()
            try:
                uuid_a = UUID(uuid_a_raw)
                uuid_b = UUID(uuid_b_raw)
            except ValueError:
                raise DatasetImportError(filename, row_no, "image_a/image_b must be valid uuids")

            image_a = get_by_uuid(db, Image, uuid_a.bytes)
            image_b = get_by_uuid(db, Image, uuid_b.bytes)
            if image_a is None or image_b is None:
                raise DatasetImportError(filename, row_no, "image_a/image_b must reference existing images")
            if image_a.id == image_b.id:
                raise DatasetImportError(filename, row_no, "image_a and image_b must differ")

            id1, id2 = sorted((image_a.id, image_b.id))
            status_id = _resolve_status(
                row.get("status"), status_map, status_map[default_status], file=filename, row=row_no
            )

            try:
                create_fn(db, image1_id=id1, image2_id=id2, status_id=status_id, creator_id=creator_id)
            except (SameDiveError, ConflictError) as exc:
                raise DatasetImportError(filename, row_no, str(exc)) from exc
            count += 1
    return count


def run_import(db: Session, work_dir: Path, creator_id: int) -> tuple[ImportSummary, list[tuple[Path, Path]]]:
    """Run the whole CSV import against `work_dir` (an extracted zip root).

    Processes each optional CSV in dependency order - labels, cameras,
    regions, dives, images, candidates, pairs - flushing each row so later
    CSVs can resolve references to rows created earlier in the same import.
    Fails fast on the first error (raises `DatasetImportError`); does not
    commit or touch the filesystem beyond staging image files into
    `ASSETS_DIR/.tmp` (returned as `pending_moves`, for the caller to apply
    only after a successful commit).
    """
    summary = ImportSummary()
    summary.labels = _import_labels(db, work_dir / "labels.csv", creator_id)
    summary.cameras = _import_simple_metadata_entity(
        db, work_dir / "cameras.csv", "cameras.csv", create_camera, creator_id
    )
    summary.regions = _import_simple_metadata_entity(
        db, work_dir / "regions.csv", "regions.csv", create_region, creator_id
    )
    summary.dives = _import_dives(db, work_dir / "dives.csv", creator_id)
    summary.images, pending_moves = _import_images(
        db, work_dir / "images.csv", work_dir / "images", creator_id
    )
    summary.candidate_pairs = _import_pair_csv(
        db, work_dir / "candidates.csv", "candidates.csv",
        CANDIDATE_STATUS_INT, CandidateStatus.HIDDEN, create_candidate_pair, creator_id,
    )
    summary.image_pairs = _import_pair_csv(
        db, work_dir / "pairs.csv", "pairs.csv",
        PAIR_STATUS_INT, PairStatus.HIDDEN, create_image_pair, creator_id,
    )
    return summary, pending_moves
