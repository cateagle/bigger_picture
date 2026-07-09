import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from blake3 import blake3
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
from src.schema.helper_images import HelperImage
from src.schema.images import Image
from src.schema.regions import Region
from src.services.assets import (
    detect_image_extension,
    read_image_dimensions,
    resolve_asset_path,
    stage_source_file,
)
from src.services.cameras import create_camera
from src.services.candidate_pairs import create_candidate_pair
from src.services.dives import create_dive, resolve_or_default_camera_id
from src.services.errors import ConflictError, SameDiveError
from src.services.fun_facts import create_fun_fact
from src.services.helper_images import create_helper_image
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
    helper_images: int = 0
    fun_facts: int = 0


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


def _resolve_required_fact(raw: str | None, *, file: str, row: int) -> Any:
    """Parse the required `fact` column of fun_facts.csv.

    Reuses `_resolve_metadata`'s JSON parsing, then rejects a blank/missing
    value, since `FunFact.fact_json` is NOT NULL unlike the optional
    `metadata` columns `_resolve_metadata` otherwise serves.
    """
    fact = _resolve_metadata(raw, file=file, row=row)
    if fact is None:
        raise DatasetImportError(file, row, "fact is required")
    return fact


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
) -> tuple[int, list[tuple[Path, Path]], dict[str, Image]]:
    if not csv_path.exists():
        return 0, [], {}
    if not images_root.is_dir():
        raise DatasetImportError(
            "images.csv", None, "images/ folder is required when images.csv is present"
        )

    pending: list[tuple[Path, Path]] = []
    images_by_source_path: dict[str, Image] = {}
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
                image = create_image(
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
            images_by_source_path[source_path] = image
            count += 1
    return count, pending, images_by_source_path


def _describe_pair_image(image: Image, images_by_source_path: dict[str, Image]) -> str:
    """Describe `image` for an error message: its source_path if it was
    uploaded in this same import's images.csv, otherwise its filepath/filename
    as already stored on the server.
    """
    for source_path, candidate in images_by_source_path.items():
        if candidate.id == image.id:
            return f"source_path {source_path!r}"
    return f"filepath {image.filepath!r} (filename {image.filename!r})"


def _resolve_pair_image(
    db: Session,
    uuid_col: str,
    uuid_raw: str | None,
    source_col: str,
    source_raw: str | None,
    images_by_source_path: dict[str, Image],
    *,
    file: str,
    row: int,
) -> Image:
    """Resolve one side of a candidates.csv/pairs.csv row.

    `uuid_col` (e.g. `image_a`) takes precedence over `source_col` (e.g.
    `image_source_a`) when both are given. `source_col` only matches an image
    uploaded via `images.csv` in this same import - it has no way to look up
    a pre-existing image, since only images.csv rows carry a source_path.
    """
    uuid_raw = (uuid_raw or "").strip()
    source_raw = (source_raw or "").strip()
    if uuid_raw:
        try:
            uuid_value = UUID(uuid_raw)
        except ValueError:
            raise DatasetImportError(file, row, f"{uuid_col} must be a valid uuid: {uuid_raw!r}")
        image = get_by_uuid(db, Image, uuid_value.bytes)
        if image is None:
            raise DatasetImportError(file, row, f"{uuid_col} must reference an existing image: {uuid_raw!r}")
        return image
    if source_raw:
        image = images_by_source_path.get(source_raw)
        if image is None:
            raise DatasetImportError(
                file, row, f"{source_col} does not match any source_path in images.csv: {source_raw!r}"
            )
        return image
    raise DatasetImportError(file, row, f"exactly one of {uuid_col}/{source_col} must be set")


def _import_pair_csv(
    db: Session,
    path: Path,
    filename: str,
    status_map: dict[str, int],
    default_status: str,
    create_fn,
    creator_id: int,
    images_by_source_path: dict[str, Image],
) -> int:
    """Shared row processing for candidates.csv/pairs.csv: image_a/image_source_a,
    image_b/image_source_b, status."""
    if not path.exists():
        return 0
    count = 0
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row_no, row in enumerate(reader, start=2):
            image_a = _resolve_pair_image(
                db, "image_a", row.get("image_a"), "image_source_a", row.get("image_source_a"),
                images_by_source_path, file=filename, row=row_no,
            )
            image_b = _resolve_pair_image(
                db, "image_b", row.get("image_b"), "image_source_b", row.get("image_source_b"),
                images_by_source_path, file=filename, row=row_no,
            )
            if image_a.id == image_b.id:
                raise DatasetImportError(
                    filename, row_no,
                    f"image_a and image_b must differ ({_describe_pair_image(image_a, images_by_source_path)})",
                )

            id1, id2 = sorted((image_a.id, image_b.id))
            status_id = _resolve_status(
                row.get("status"), status_map, status_map[default_status], file=filename, row=row_no
            )

            try:
                create_fn(db, image1_id=id1, image2_id=id2, status_id=status_id, creator_id=creator_id)
            except (SameDiveError, ConflictError) as exc:
                raise DatasetImportError(
                    filename, row_no,
                    f"{exc} ({_describe_pair_image(image_a, images_by_source_path)} / "
                    f"{_describe_pair_image(image_b, images_by_source_path)})",
                ) from exc
            count += 1
    return count


def _import_helper_images(
    db: Session, csv_path: Path, helper_images_root: Path, creator_id: int
) -> tuple[int, list[tuple[Path, Path]]]:
    if not csv_path.exists():
        return 0, []
    if not helper_images_root.is_dir():
        raise DatasetImportError(
            "helper_images.csv", None, "helper_images/ folder is required when helper_images.csv is present"
        )

    pending: list[tuple[Path, Path]] = []
    count = 0
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row_no, row in enumerate(reader, start=2):
            helper_image_uuid = _resolve_uuid_field(row.get("uuid"), file="helper_images.csv", row=row_no)

            source_path = (row.get("source_path") or "").strip()
            if not source_path:
                raise DatasetImportError("helper_images.csv", row_no, "source_path is required")
            try:
                source_file = resolve_asset_path(source_path, base_dir=helper_images_root)
            except ValueError as exc:
                raise DatasetImportError("helper_images.csv", row_no, f"invalid source_path: {exc}") from exc
            if not source_file.is_file():
                raise DatasetImportError(
                    "helper_images.csv", row_no, f"source file not found: {source_path!r}"
                )

            filename = (row.get("filename") or "").strip() or source_path
            explicit_filepath = (row.get("filepath") or "").strip()
            if explicit_filepath:
                try:
                    final_dest = resolve_asset_path(explicit_filepath)
                except ValueError as exc:
                    raise DatasetImportError(
                        "helper_images.csv", row_no, f"invalid filepath: {exc}"
                    ) from exc

            temp_path = stage_source_file(source_file)
            try:
                read_image_dimensions(temp_path)
            except ValueError as exc:
                temp_path.unlink(missing_ok=True)
                raise DatasetImportError(
                    "helper_images.csv", row_no, f"could not decode image: {exc}"
                ) from exc

            digest = blake3(temp_path.read_bytes()).digest()

            if explicit_filepath:
                filepath = explicit_filepath
            else:
                try:
                    ext = detect_image_extension(temp_path)
                except ValueError as exc:
                    temp_path.unlink(missing_ok=True)
                    raise DatasetImportError(
                        "helper_images.csv", row_no, f"could not detect image type: {exc}"
                    ) from exc
                filepath = f"helper_images/{digest.hex()}.{ext}"
                final_dest = resolve_asset_path(filepath)

            try:
                create_helper_image(
                    db,
                    uuid=helper_image_uuid,
                    filepath=filepath,
                    filename=filename,
                    blake3_hash=digest,
                    creator_id=creator_id,
                )
            except ConflictError as exc:
                temp_path.unlink(missing_ok=True)
                raise DatasetImportError("helper_images.csv", row_no, str(exc)) from exc

            pending.append((temp_path, final_dest))
            count += 1
    return count, pending


def _import_fun_facts(db: Session, path: Path, creator_id: int) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row_no, row in enumerate(reader, start=2):
            uuid_value = _resolve_uuid_field(row.get("uuid"), file="fun_facts.csv", row=row_no)
            title = (row.get("title") or "").strip()
            if not title:
                raise DatasetImportError("fun_facts.csv", row_no, "title is required")
            fact = _resolve_required_fact(row.get("fact"), file="fun_facts.csv", row=row_no)

            min_level_raw = _resolve_optional_int(
                row.get("min_level"), field="min_level", file="fun_facts.csv", row=row_no
            )
            min_level = min_level_raw if min_level_raw is not None else 0

            region = _resolve_ref(
                db, Region, row.get("region_uuid"), row.get("region_title"),
                file="fun_facts.csv", row=row_no, kind="region",
            )
            # No image_title column: HelperImage has no unique display name to
            # look up by, so title_raw is hardcoded None here.
            image = _resolve_ref(
                db, HelperImage, row.get("image_uuid"), None,
                file="fun_facts.csv", row=row_no, kind="image",
            )

            try:
                create_fun_fact(
                    db,
                    uuid=uuid_value,
                    title=title,
                    fact=fact,
                    min_level=min_level,
                    region_id=region.id if region else None,
                    image_id=image.id if image else None,
                    creator_id=creator_id,
                )
            except ConflictError as exc:
                raise DatasetImportError("fun_facts.csv", row_no, str(exc)) from exc
            count += 1
    return count


def run_import(db: Session, work_dir: Path, creator_id: int) -> tuple[ImportSummary, list[tuple[Path, Path]]]:
    """Run the whole CSV import against `work_dir` (an extracted zip root).

    Processes each optional CSV in dependency order - labels, cameras,
    regions, dives, images, candidates, pairs, helper_images, fun_facts -
    flushing each row so later CSVs can resolve references to rows created
    earlier in the same import. Fails fast on the first error (raises
    `DatasetImportError`); does not commit or touch the filesystem beyond
    staging image files into `ASSETS_DIR/.tmp` (returned as `pending_moves`,
    for the caller to apply only after a successful commit).
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
    summary.images, pending_moves, images_by_source_path = _import_images(
        db, work_dir / "images.csv", work_dir / "images", creator_id
    )
    summary.candidate_pairs = _import_pair_csv(
        db, work_dir / "candidates.csv", "candidates.csv",
        CANDIDATE_STATUS_INT, CandidateStatus.HIDDEN, create_candidate_pair, creator_id,
        images_by_source_path,
    )
    summary.image_pairs = _import_pair_csv(
        db, work_dir / "pairs.csv", "pairs.csv",
        PAIR_STATUS_INT, PairStatus.HIDDEN, create_image_pair, creator_id,
        images_by_source_path,
    )
    summary.helper_images, helper_image_moves = _import_helper_images(
        db, work_dir / "helper_images.csv", work_dir / "helper_images", creator_id
    )
    pending_moves += helper_image_moves
    summary.fun_facts = _import_fun_facts(db, work_dir / "fun_facts.csv", creator_id)
    return summary, pending_moves
