from pathlib import Path
import csv
import argparse

# Parser for Input/Output Argument
parser = argparse.ArgumentParser(
    description="Generate image pairs from a directory."
)
parser.add_argument(
    "image_dir",
    type=Path,
    help="Path to the directory containing the images"
)
parser.add_argument(
    "-o", "--output",
    default="image_pairs.csv",
    help="Output CSV file (default: image_pairs.csv)"
)
parser.add_argument(
    "-n", "--num-subsequent",
    type=int,
    default=5,
    help="Number of subsequent images to pair with each image (default: 5)"
)

args = parser.parse_args()

# Output CSV
output_csv = args.output

# Supported image extensions
extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".gif", ".webp"}

# Read and sort image filenames
image_names = sorted(
    f.name for f in args.image_dir.iterdir()
    if f.is_file() and f.suffix.lower() in extensions
)

# Number of subsequent images to pair with
num_subsequent = args.num_subsequent

# Generate pairs
pairs = []
for i in range(len(image_names)):
    for j in range(i + 1, min(i + 1 + num_subsequent, len(image_names))):
        pairs.append((image_names[i], image_names[j]))

# Write to CSV
with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["image_1", "image_2"])
    writer.writerows(pairs)

print(f"Saved {len(pairs)} image pairs to {output_csv}")