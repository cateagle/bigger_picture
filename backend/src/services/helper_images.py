from blake3 import blake3
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.schema.helper_images import HelperImage
from src.services.assets import (
    detect_image_extension,
    move_asset,
    read_image_dimensions,
    resolve_asset_path,
    write_temp_image,
)
from src.util import new_uuid, now_ms


def get_or_create_helper_image(
    db: Session, *, image_b64: str, filename: str, creator_id: int,
) -> HelperImage:
    """Decode `image_b64`, hash it, and return the matching `HelperImage` row -
    creating it (and writing the file) only if no row with that hash exists.

    filepath is `helper_images/{hex_digest}.{ext}`, with `ext` detected from
    the decoded content (never from `filename`, which is display-only).
    Dedup is keyed on `blake3_hash`, not on parsing filepath.

    Commits internally, unlike other create_* services: this is a get-or-create
    against a hashed/unique asset that must resolve concurrent duplicate
    uploads atomically, is called from two independent routes (fun_facts
    create and update), and - once ingested - is a standalone reusable asset
    that must survive even if the caller's own fun_fact write later fails for
    an unrelated reason (e.g. duplicate title).

    Raises `ValueError` on invalid base64 or undecodable image content (the
    caller maps this to a 422).
    """
    temp_path = write_temp_image(image_b64)  # raises ValueError on bad base64
    try:
        read_image_dimensions(temp_path)  # raises ValueError if undecodable; dimensions unused - helper_images has no size columns
        data = temp_path.read_bytes()
        digest = blake3(data).digest()

        existing = db.execute(
            select(HelperImage).where(HelperImage.blake3_hash == digest)
        ).scalar_one_or_none()
        if existing is not None:
            temp_path.unlink(missing_ok=True)
            return existing

        ext = detect_image_extension(temp_path)  # raises ValueError if the format is unrecognized
        filepath = f"helper_images/{digest.hex()}.{ext}"
        dest = resolve_asset_path(filepath)

        helper_image = HelperImage(
            uuid=new_uuid().bytes,
            created_at=now_ms(),
            created_by=creator_id,
            filepath=filepath,
            filename=filename,
            blake3_hash=digest,
        )
        db.add(helper_image)
        try:
            db.commit()
        except IntegrityError:
            # Lost a race against a concurrent identical upload.
            db.rollback()
            temp_path.unlink(missing_ok=True)
            return db.execute(
                select(HelperImage).where(HelperImage.blake3_hash == digest)
            ).scalar_one()

        move_asset(temp_path, dest)  # commit-then-move, mirroring update_image
        db.refresh(helper_image)
        return helper_image
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
