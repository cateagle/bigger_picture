import base64
from pathlib import Path, PurePosixPath

import cv2

from src import config


def resolve_asset_path(filepath: str) -> Path:
    """Resolve `filepath` under `config.ASSETS_DIR`, rejecting traversal.

    `filepath` must be a relative path referencing a file *within* the assets
    directory. Defense-in-depth checks, each raising `ValueError`:

    - empty `filepath`, or one containing a NUL byte;
    - absolute paths (either `Path.is_absolute()` or a leading `/`);
    - any path with a `..` component;
    - a path that resolves to the assets directory itself (must be a file
      within it, not the root).

    The final `is_relative_to` guard on the resolved path is the real
    backstop: because `.resolve()` follows symlinks, it also catches escapes
    via symlinked components.
    """
    if not filepath or "\x00" in filepath:
        raise ValueError(f"Invalid asset filepath: {filepath!r}")
    if Path(filepath).is_absolute() or filepath.startswith("/"):
        raise ValueError(f"Absolute asset filepath not allowed: {filepath!r}")
    if ".." in PurePosixPath(filepath).parts:
        raise ValueError(f"Path traversal not allowed: {filepath!r}")

    assets_dir = Path(config.ASSETS_DIR).resolve()
    resolved = (assets_dir / filepath).resolve()
    if resolved == assets_dir:
        raise ValueError(f"Asset filepath must reference a file: {filepath!r}")
    if not resolved.is_relative_to(assets_dir):
        raise ValueError(f"Path escapes assets directory: {filepath!r}")
    return resolved


def write_base64_image(dest: Path, b64: str) -> None:
    """Decode a base64 image and write its bytes to `dest`."""
    data = base64.b64decode(b64)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def read_image_dimensions(path: Path) -> tuple[int, int]:
    """Return `(size_x, size_y)` = `(width, height)` of the image at `path`.

    `cv2.imread` yields an array shaped `(height, width, channels)`. Raises
    `ValueError` if the image cannot be decoded.
    """
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not decode image: {path}")
    height = image.shape[0]
    width = image.shape[1]
    return (width, height)
