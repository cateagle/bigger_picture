#!/usr/bin/env python3
"""Generate the two CSVs that upload_dataset.py consumes from an image folder.

Discovers the images in a directory (sorted by filename), assigns each a uuid,
and pairs each image with its N subsequent neighbours. Writes:

  - an images CSV (filename,uuid) - the uuid list of images
  - a pairs CSV (image1,image2)  - the same uuids, one row per pair

Both are directly usable as upload_dataset.py's --files-csv and --pairs-csv.

Re-running is stable: any filename already present in the images CSV keeps its
existing uuid, so only newly-added images get fresh ones. This avoids handing
the same file a new uuid on every run (which would upload duplicates).
"""

import argparse
import csv
import uuid
from pathlib import Path

# Supported image extensions
EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".gif", ".webp"}

# Column headers, matching what upload_dataset.py expects for each CSV.
FILES_HEADER = ["filename", "uuid"]
PAIRS_HEADER = ["image1", "image2"]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image_dir", type=Path, help="Directory containing the images")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("image_pairs.csv"),
        help="Output pairs CSV (default: image_pairs.csv)",
    )
    parser.add_argument(
        "-u", "--images-output", type=Path, default=Path("images.csv"),
        help="Output images/uuid CSV (default: images.csv)",
    )
    parser.add_argument(
        "-n", "--num-subsequent", type=int, default=5,
        help="Number of subsequent images to pair with each image (default: 5)",
    )
    return parser.parse_args(argv)


def find_images(image_dir: Path) -> list[str]:
    """Return image filenames in the directory, sorted."""
    return sorted(
        f.name for f in image_dir.iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSIONS
    )


def load_existing_uuids(images_csv: Path) -> dict[str, str]:
    """Return the filename -> uuid map already recorded in `images_csv`, if any.

    Lets re-runs keep uuids stable so previously-uploaded images aren't given a
    new identity (which would create duplicates on the server).
    """
    if not images_csv.exists():
        return {}
    with images_csv.open(newline="", encoding="utf-8") as fh:
        return {
            row["filename"]: row["uuid"]
            for row in csv.DictReader(fh)
            if row.get("filename") and row.get("uuid")
        }


def assign_uuids(image_names: list[str], existing: dict[str, str]) -> dict[str, str]:
    """Map each filename to a uuid, reusing any existing assignment."""
    return {name: existing.get(name) or str(uuid.uuid4()) for name in image_names}


def build_pairs(image_names: list[str], num_subsequent: int) -> list[tuple[str, str]]:
    """Pair each image with up to `num_subsequent` following images."""
    pairs = []
    for i, name in enumerate(image_names):
        for j in range(i + 1, min(i + 1 + num_subsequent, len(image_names))):
            pairs.append((name, image_names[j]))
    return pairs


def write_csv(path: Path, header: list[str], rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def main(argv=None):
    args = parse_args(argv)

    image_names = find_images(args.image_dir)
    if not image_names:
        raise SystemExit(f"No images found in {args.image_dir}")

    ids = assign_uuids(image_names, load_existing_uuids(args.images_output))
    pairs = build_pairs(image_names, args.num_subsequent)

    write_csv(args.images_output, FILES_HEADER, ((name, ids[name]) for name in image_names))
    write_csv(args.output, PAIRS_HEADER, ((ids[a], ids[b]) for a, b in pairs))

    print(f"Saved {len(image_names)} images to {args.images_output}")
    print(f"Saved {len(pairs)} image pairs to {args.output}")


if __name__ == "__main__":
    main()
