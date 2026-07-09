# Uploading a dataset as a zip file

This page explains how to prepare a zip file so it can be uploaded in one step and turned into
labels, regions, cameras, dives, images, image pairs, helper images, and fun facts in the system.

Example files are in [`zip-uploads-examples/`](zip-uploads-examples/) and
are referenced throughout this page.

## What goes into the zip file

The zip file can contain up to nine tables (as CSV files) and two folders of pictures:

| File                | Contains                                                          |
|---------------------|--------------------------------------------------------------------|
| `labels.csv`        | Labels that can later be attached to a point in an image         |
| `cameras.csv`       | The cameras that took the pictures                               |
| `regions.csv`       | The general areas or sites a dive took place in                  |
| `dives.csv`         | Individual dives, each linked to a region and a camera           |
| `images.csv`        | The pictures themselves, each linked to a dive                   |
| `candidates.csv`    | Pairs of images to be checked for overlap                        |
| `pairs.csv`         | Pairs of images that are already known to overlap                |
| `helper_images.csv` | Decorative images, for example ones attached to fun facts        |
| `fun_facts.csv`     | Short facts that can be shown to users                           |
| `images/`           | A folder containing the actual picture files for `images.csv`    |
| `helper_images/`    | A folder containing the actual picture files for `helper_images.csv` |

All nine files are optional. If you are only adding pictures to dives that already exist, you only need `images.csv` and the `images/` folder. Leave out any file you don't need.

The file names must be spelled exactly as above (lower case, with the `.csv` ending), and the `images/` and `helper_images/` folders must be named exactly that. They all sit next to each other at the top level of the zip file, not inside another folder.

## General rules for every table

- Save each table as a plain CSV file, not as an Excel or Numbers file.
- Use a semicolon `;`, not a comma, to separate columns.
- Save the file with UTF-8 text encoding, so accented letters and special characters are kept intact. Most spreadsheet programs offer this as an option when saving or exporting (for example "CSV UTF-8" in Excel).
- The first row of every file must contain the column names exactly as shown in this page. The order of the columns does not matter, only their names.
- Leave a cell empty for any column marked "optional" that does not apply to that row.
- Because semicolons separate columns, avoid using a semicolon inside a title, description, or any other piece of free text. If you cannot avoid it, put quotation marks around the whole piece of text (`"like this; with a semicolon inside"`). Most spreadsheet programs do this automatically when needed.

## Identifiers, and the `new` shortcut

Every region, camera, dive, image, label, helper image, and fun fact needs a UUID so it can be told apart from every other one, even if two of them have the exact same name. For almost every row you create, you can simply write:

```
new
```

in the identifier column, and the system will generate an identifier for you automatically.

The one case where you need to provide your own identifier is when you want to attach a helper image to a fun fact in `fun_facts.csv` (see below) - that file can only refer to a helper image by its identifier, not by name, and identifiers generated with `new` are never shown back to you. `candidates.csv` and `pairs.csv` can link two images together the same way, by identifier, but they can also link a picture by the same `source_path` you gave it in `images.csv` instead, so you do not need to invent an identifier for images unless you prefer to. Whenever you do need your own identifier, invent one in the format shown in the example files, for instance:

```
dd9c02f4-eef3-4806-a5fa-302e56676954
```

Any combination of the digits 0-9 and the letters a-f, arranged in that pattern of groups (8-4-4-4-12 characters, separated by dashes), works. You are also free to invent your own identifier for a region, camera, dive, or label instead of writing `new`, if you prefer. It makes no difference, since those can always be referred to by name afterwards regardless of how their identifier was chosen.

## Referring to something you created elsewhere in the zip

Dives need to say which region and camera they belong to, images need to say which dive they belong to, and fun facts can optionally say which region they are scoped to. For these links, most tables offer **two columns**: one ending in `_uuid` and one ending in `_title`. Fill in only one of them:

- Fill in the `_title` column with the exact name you gave the region, camera, or dive elsewhere in the zip (or that it already has in the system). This is the simplest option and works whether that region, camera, or dive was just created with `new` in this same upload, or already existed beforehand.
- Fill in the `_uuid` column instead if you already know the exact identifier.
- If you fill in both, the identifier is used and the name is ignored.
- Leave both empty only where the table below says that is allowed.

`candidates.csv` and `pairs.csv` offer a variant of this same idea: instead of a `_title` column, they offer an `image_source_a`/`image_source_b` column, keyed off the `source_path` you gave the picture in `images.csv` rather than off a name. The same rule applies if you fill in both `image_a` and `image_source_a`, the identifier is used and the `source_path` is ignored. See the `candidates.csv` section below for details.

## What happens when you upload the zip file

The tables are read in a fixed order:
1. labels
2. cameras
3. regions
4. dives
5. images
6. candidates
7. pairs
8. helper images
9. fun facts

This means a dive can refer to a region from `regions.csv` in the same zip, but a region cannot refer to a dive, because regions are read first. Likewise, a fun fact can refer to a helper image from `helper_images.csv` in the same zip, because helper images are read first.

The upload is all or nothing: if anything in the zip file cannot be understood. A name that does not match anything, a picture that is missing, a misspelled column, nothing at all is added and you are told exactly which file and which row caused the problem. Partial uploads never happen.

Once the upload succeeds, you get back a count of how many labels, cameras, regions, dives, images, candidate pairs, image pairs, helper images, and fun facts were created. Identifiers that were generated automatically with `new` are not listed individually, so if you plan to look a specific row up again afterwards, give it its own name (title) or your own identifier rather than relying on `new`.

## Table reference

### `labels.csv`

A label is a short tag that can later be attached to a point marked in an image (for example, marking that a point shows coral).

| Column        | Required | What to put there                             |
|---------------|----------|-----------------------------------------------|
| `uuid`        | Yes      | `new`, or your own identifier                 |
| `scope`       | Yes      | A short category name grouping related labels together. The combination of scope and title must be unique. |
| `title`       | Yes      | The name of the label, for example `Coral`    |
| `description` | Optional | A longer explanation of what the label means  |

Example ([`labels.csv`](zip-uploads-examples/labels.csv)):

| uuid                                 | scope            | title  | description       |
|--------------------------------------|------------------|--------|-------------------|
| new                                  | point-annotation | Coral  | Hard coral colony |
| d2921956-4d60-48e1-a423-f51276d29d92 | point-annotation | Sponge |                   |

The second label is given its own identifier instead of `new`, and leaves the optional description empty. Both are valid.

### `cameras.csv`

| Column        | Required | What to put there                       |
|---------------|----------|-----------------------------------------|
| `uuid`        | Yes      | `new`, or your own identifier           |
| `title`       | Yes      | The name of the camera. Must be unique. |
| `metadata`    | Optional | Extra details about the camera, written as `{"key": "value"}` pairs on a single line. Leave empty if not needed. |
| `description` | Optional | A longer description of the camera      |

Example ([`cameras.csv`](zip-uploads-examples/cameras.csv)):

| uuid                                 | title         | metadata             | description                      |
|--------------------------------------|---------------|----------------------|----------------------------------|
| new                                  | ROV Camera 1  | {"resolution": "4K"} | Forward-facing camera on the ROV |
| 3f2bde7f-eca5-4e39-8005-aef528f9f65c | Drop Camera 2 |                      |                                  |

The second camera leaves both optional columns empty, and uses its own identifier instead of `new` so that a later dive can refer to it by identifier instead of by name (see `dives.csv` below), either works.

### `regions.csv`

| Column        | Required | What to put there                                                   |
|---------------|----------|---------------------------------------------------------------------|
| `uuid`        | Yes      | `new`, or your own identifier                                       |
| `title`       | Yes      | The name of the region or site. Must be unique.                     |
| `metadata`    | Optional | Extra details, written as `{"key": "value"}` pairs on a single line |
| `description` | Optional | A longer description of the region                                  |

Example ([`regions.csv`](zip-uploads-examples/regions.csv)):

| uuid                                 | title                       | metadata | description                    |
|--------------------------------------|-----------------------------|----------|--------------------------------|
| new                                  | Reykjanes Ridge             |          | Mid-Atlantic ridge survey area |
| 07bd8168-d881-4ca9-8c16-b14f974af44b | Charlie-Gibbs Fracture Zone | {"survey_year": 2024} |                   |

The two rows show the two optional columns filled in either order: metadata left empty with a description in the first row, and metadata filled in with the description left empty in the second.

### `dives.csv`

Each dive belongs to one region, and one camera.

| Column         | Required | What to put there                                                   |
|----------------|----------|---------------------------------------------------------------------|
| `uuid`         | Yes      | `new`, or your own identifier                                       |
| `title`        | Yes      | The name of the dive. Must be unique.                               |
| `metadata`     | Optional | Extra details, written as `{"key": "value"}` pairs on a single line |
| `description`  | Optional | A longer description of the dive                                    |
| `region_uuid`  | See note | The region's identifier                                             |
| `region_title` | See note | The region's name                                                   |
| `camera_uuid`  | Optional | The camera's identifier                                             |
| `camera_title` | Optional | The camera's name                                                   |

Fill in exactly one of `region_uuid`/`region_title`. A dive always needs a region. The camera columns can both be left empty; in that case the dive is automatically assigned to a placeholder camera named "Unknown Camera", which you can correct later once the real camera is known.

Example ([`dives.csv`](zip-uploads-examples/dives.csv)):

| uuid | title | metadata | description | region_uuid | region_title | camera_uuid | camera_title |
|------|-------|----------|--------------|-------------|--------------|-------------|----------------|
| new | Dive 2024-05-12 Site A | {"max_depth_m": 1200} | | | Reykjanes Ridge | | ROV Camera 1 |
| new | Dive 2024-05-14 Site B | | | | Reykjanes Ridge | | |
| a87c4623-7678-4b29-8522-6ab33b93cf3c | Dive 2024-06-02 Site C | | Follow-up survey of the fracture zone | 07bd8168-d881-4ca9-8c16-b14f974af44b | | 3f2bde7f-eca5-4e39-8005-aef528f9f65c | |

These three rows cover every option:
- The first dive finds its region and camera **by name** (`region_title`, `camera_title`).
- The second dive leaves both camera columns empty, so it is assigned to the placeholder "Unknown Camera".
- The third dive finds its region and camera **by identifier** (`region_uuid`, `camera_uuid`) instead, referring back to the second row of `regions.csv` and `cameras.csv` above, and is itself given its own identifier rather than `new`, so that `images.csv` below can refer to it by identifier too.

### `images.csv`

Each row describes one picture and links it to a dive. The picture file itself must be included in the `images/` folder of the zip (see below). This table only describes it, it does not contain the picture.

| Column        | Required | What to put there                                                                                           |
|---------------|----------|-------------------------------------------------------------------------------------------------------------|
| `uuid`        | Yes      | `new`, or your own identifier. You only need your own identifier here if you plan to link this picture in `candidates.csv`/`pairs.csv` by identifier - linking it by `source_path` instead does not require one (see below). |
| `source_path` | Yes      | Where to find the picture file inside the `images/` folder, for example `dive-a/frame_0001.jpg`             |
| `filename`    | Optional | The display name for the picture. Leave empty to reuse `source_path`.                                       |
| `filepath`    | Optional | Where the picture should be permanently stored. Leave empty and a filepath will be generated automatically. |
| `dive_uuid`   | See note | The dive's identifier                                                                                       |
| `dive_title`  | See note | The dive's name                                                                                             |
| `status`      | Optional | See [Status values](#status-values). Leave empty to use the default.                                        |
| `metadata`    | Optional | Extra details, written as `{"key": "value"}` pairs on a single line                                         |
| `difficulty`  | Optional | A whole number you can use to mark how difficult the picture is, if you use that in your workflow           |
| `priority`    | Optional | A whole number you can use to mark how important the picture is, if you use that in your workflow           |

Fill in exactly one of `dive_uuid`/`dive_title`. Every image needs a dive.

Example ([`images.csv`](zip-uploads-examples/images.csv)):

| uuid | source_path  | filename | filepath | dive_uuid | dive_title | status | metadata | difficulty | priority |
|------|--------------|----------|----------|-----------|--------------|--------|----------|------------|----------|
| dd9c02f4-eef3-4806-a5fa-302e56676954 | dive-a/frame_0001.jpg | | | | Dive 2024-05-12 Site A | | | | |
| 3d2d6a96-a537-4eb2-801c-babdaab57bc4 | dive-a/frame_0002.jpg | Site A - frame 2 | | | Dive 2024-05-12 Site A | open | {"iso": 200} | 2 | 5 |
| 41f6aea3-cbf8-48f9-ac01-ec7afdbacb2b | dive-a/frame_0003.jpg | | dive-a-highlights/frame_0003.jpg | | Dive 2024-05-12 Site A | | | | |
| new | dive-b/frame_0001.jpg | | | | Dive 2024-05-14 Site B | | | | |
| new | dive-c/frame_0001.jpg | Site C overview | | a87c4623-7678-4b29-8522-6ab33b93cf3c | | review_pending | | 4 | |
| new | dive-c/frame_0002.jpg | | | a87c4623-7678-4b29-8522-6ab33b93cf3c | | | | | |

These six rows cover every option:

- The first image leaves every optional column empty: its display name falls back to `source_path`, its permanent location is chosen automatically, its status defaults to hidden, and it has no metadata, difficulty, or priority.
- The second image sets every optional column: a display name, an explicit status, metadata, a difficulty, and a priority.
- The third image sets its own `filepath`, overriding where the picture is permanently stored instead of leaving it to be chosen automatically.
- The fourth image belongs to a dive found **by name** (`dive_title`) and is given `new` as its identifier, since nothing needs to refer back to it.
- The fifth and sixth images belong to a dive found **by identifier** (`dive_uuid`) instead, referring back to the third row of `dives.csv` above. The fifth also sets a display name, a status, and a difficulty, while leaving priority empty, to show that the optional columns can be mixed and matched independently of one another.

The first three images are given their own identifiers, since they are linked together below, in `candidates.csv` and `pairs.csv`, by identifier. The rest are not, since `candidates.csv` and `pairs.csv` can also link a picture by the same `source_path` you gave it here, without needing an identifier of your own.

### `candidates.csv`

Pairs of images that should be checked for overlap. Both images must belong to the same dive.

Each image can be identified in either of two ways - fill in exactly one per side:

| Column           | Required | What to put there                                                                              |
|------------------|----------|--------------------------------------------------------------------------------------------------|
| `image_a`        | See note | The identifier of the first image                                                              |
| `image_b`        | See note | The identifier of the second image                                                             |
| `image_source_a` | See note | The `source_path` you gave the first image in `images.csv`, in this same zip                    |
| `image_source_b` | See note | The `source_path` you gave the second image in `images.csv`, in this same zip                   |
| `status`         | Optional | See [Status values](#status-values). Leave empty to use the default.                            |

Fill in exactly one of `image_a`/`image_source_a`, and exactly one of `image_b`/`image_source_b` - the two sides are resolved independently, so it is fine to identify one image by identifier and the other by `source_path` in the same row. If you fill in both for one side, the identifier is used and the `source_path` is ignored. `image_source_a`/`image_source_b` only work for pictures included in `images.csv` in this same zip - a picture that already existed in the system before this upload can only be linked by its identifier.

Example ([`candidates.csv`](zip-uploads-examples/candidates.csv)):

| image_a                              | image_b                              | image_source_a         | image_source_b         | status      |
|---------------------------------------|---------------------------------------|-------------------------|-------------------------|-------------|
| dd9c02f4-eef3-4806-a5fa-302e56676954 | 3d2d6a96-a537-4eb2-801c-babdaab57bc4 |                         |                         |             |
| dd9c02f4-eef3-4806-a5fa-302e56676954 | 41f6aea3-cbf8-48f9-ac01-ec7afdbacb2b |                         |                         | has_overlap |
|                                       |                                       | dive-c/frame_0001.jpg  | dive-c/frame_0002.jpg  |             |

The first row leaves the status empty (defaulting to hidden); the second sets it explicitly. The third links two pictures from `images.csv` that were given `new` as their own identifier, by their `source_path` instead - referring back to the fifth and sixth rows of `images.csv` above.

### `pairs.csv`

Pairs of images that are already known to overlap and are ready to be shown to players for point-by-point matching. Both images must belong to the same dive.

Identified the same way as `candidates.csv` above:

| Column           | Required | What to put there                                                             |
|------------------|----------|-------------------------------------------------------------------------------|
| `image_a`        | See note | The identifier of the first image                                             |
| `image_b`        | See note | The identifier of the second image                                            |
| `image_source_a` | See note | The `source_path` you gave the first image in `images.csv`, in this same zip  |
| `image_source_b` | See note | The `source_path` you gave the second image in `images.csv`, in this same zip |
| `status`         | Optional | See [Status values](#status-values). Leave empty to use the default.          |

Example ([`pairs.csv`](zip-uploads-examples/pairs.csv)):

| image_a                              | image_b                              | image_source_a        | image_source_b        | status    |
|--------------------------------------|--------------------------------------|-----------------------|-----------------------|-----------|
| dd9c02f4-eef3-4806-a5fa-302e56676954 | 3d2d6a96-a537-4eb2-801c-babdaab57bc4 |                       |                       |           |
| 3d2d6a96-a537-4eb2-801c-babdaab57bc4 | 41f6aea3-cbf8-48f9-ac01-ec7afdbacb2b |                       |                       | finalized |
|                                      |                                      | dive-c/frame_0001.jpg | dive-c/frame_0002.jpg |           |

As with `candidates.csv`, the first row leaves the status empty and the second sets it explicitly. The third links the same two pictures as the `candidates.csv` example above by `source_path`; a pair does not need to have appeared in `candidates.csv` first.

When a row is rejected - for example because both images are the same, or because they belong to different dives - the error message always identifies each image, either by the `source_path` it was given in this same zip, or, for a picture already in the system before this upload, by its stored filepath and filename.

### `helper_images.csv`

A helper image is a decorative picture, for example one shown alongside a fun fact. Unlike `images.csv`, a helper image is not linked to a dive. The picture file itself must be included in the `helper_images/` folder of the zip (see below).

| Column        | Required | What to put there                                                                                                                          |
|---------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `uuid`        | Yes      | `new`, or your own identifier (give it your own if you plan to attach it to a fun fact in `fun_facts.csv`)                                 |
| `source_path` | Yes      | Where to find the picture file inside the `helper_images/` folder, for example `jellyfish.jpg`                                             |
| `filename`    | Optional | The display name for the picture. Leave empty to reuse `source_path`.                                                                      |
| `filepath`    | Optional | Where the picture should be permanently stored. Leave empty and a filepath will be generated automatically from the picture's own content. |

Example ([`helper_images.csv`](zip-uploads-examples/helper_images.csv)):

| uuid                                 | source_path    | filename            | filepath             |
|--------------------------------------|----------------|---------------------|----------------------|
| bd5d95f9-040f-4c22-8d60-7e61d32f4aa2 | jellyfish.jpg  |                     |                      |
| af5fa30f-017f-4eca-bb91-59ae74c7e890 | anglerfish.jpg | Deep Sea Anglerfish |                      |
| 83b8efab-a751-44fc-9a90-da3b647054e0 | coral-icon.png |                     | icons/coral-icon.png |

These three rows cover every option:
- The first helper image leaves every optional column empty: its display name falls back to `source_path`, and its permanent location is chosen automatically from the picture's own content.
- The second helper image sets a display name, but still lets its storage location be chosen automatically.
- The third helper image sets its own `filepath`, overriding where the picture is permanently stored instead of leaving it to be chosen automatically.

All three helper images are given their own identifiers instead of `new`, since they are attached to fun facts below, in `fun_facts.csv`.

### `fun_facts.csv`

A fun fact is a short piece of trivia that can be shown to users, optionally scoped to a region and decorated with a helper image.

| Column         | Required | What to put there                                                                                                    |
|----------------|----------|--------------------------------------------------------------------------------------------------------------------------|
| `uuid`         | Yes      | `new`, or your own identifier                                                                                        |
| `title`        | Yes      | The name of the fun fact. Must be unique.                                                                            |
| `fact`         | Yes      | The fact itself, written as a JSON object on a single line, for example `{"body": "..."}`. Unlike every other JSON column on this page, this one may not be left empty. |
| `min_level`    | Optional | A whole number: the minimum expert level a user must have to be shown this fact. Leave empty to default to `0`, meaning every user can see it. |
| `region_uuid`  | Optional | The region's identifier, to limit this fact to one region                                                            |
| `region_title` | Optional | The region's name, to limit this fact to one region                                                                  |
| `image_uuid`   | Optional | The identifier of a helper image (from `helper_images.csv`, or one already in the system) to show alongside this fact |

Fill in at most one of `region_uuid`/`region_title`; leave both empty for a fact that applies to every region. Unlike every other reference in this page, there is no `image_title` column: a helper image has no unique display name to look it up by, so it can only be referred to by its identifier.

Example ([`fun_facts.csv`](zip-uploads-examples/fun_facts.csv)):

| uuid | title | fact | min_level | region_uuid | region_title | image_uuid |
|------|-------|------|-----------|-------------|--------------|------------|
| new | Deep Sea Pressure | {"body": "At 1000m depth, pressure exceeds 100 atmospheres."} | | | Reykjanes Ridge | bd5d95f9-040f-4c22-8d60-7e61d32f4aa2 |
| new | Bioluminescence | {"body": "Most deep-sea animals produce their own light."} | 2 | | | af5fa30f-017f-4eca-bb91-59ae74c7e890 |
| 0b638dab-e075-4d36-af6c-0d0d58c884f8 | General Ocean Trivia | {"body": "The ocean covers over 70% of Earth's surface."} | | | | |

These three rows cover every option:
- The first fact is scoped to a region found **by name** (`region_title`), referring back to `regions.csv`, and shows a helper image found **by identifier**, referring back to the first row of `helper_images.csv` above. It leaves `min_level` empty, defaulting to `0`.
- The second fact sets an explicit `min_level`, and shows a helper image referring back to the second row of `helper_images.csv` above, but is not scoped to any region.
- The third fact leaves region and image both empty, so it applies to every region and is shown without a picture. It is given its own identifier instead of `new`, since nothing needs to refer back to it here, but doing so makes no difference either way.

## The `images/` folder

If `images.csv` is included, the zip file must also contain a folder named `images` with the actual picture files in it. Common picture formats such as JPG, PNG, TIFF, and BMP are all accepted.

You can organize the pictures inside the `images/` folder however you like, for example in subfolders per dive, as long as the `source_path` column of `images.csv` gives the correct path to each one, measured from inside the `images/` folder. For the example above, the zip file would need to contain:

```
images/dive-a/frame_0001.jpg
images/dive-a/frame_0002.jpg
images/dive-a/frame_0003.jpg
images/dive-b/frame_0001.jpg
images/dive-c/frame_0001.jpg
images/dive-c/frame_0002.jpg
```

## The `helper_images/` folder

If `helper_images.csv` is included, the zip file must also contain a folder named `helper_images` with the actual picture files in it. The same picture formats accepted by the `images/` folder are accepted here too, and you can organize the pictures however you like, as long as `source_path` gives the correct path to each one, measured from inside the `helper_images/` folder.

Unlike `images.csv`, a helper image's automatically generated `filepath` is derived from the picture's own content rather than from its identifier. This means uploading the exact same picture bytes again under a different `uuid`, without giving an explicit `filepath`, will try to store it at the same location as before and fail as a duplicate. Give an explicit `filepath` if you intend to upload the same picture more than once.

## Status values

Images, candidate pairs, and image pairs each move through a small set of named stages. Leaving the `status` column empty always uses the first value in the list below (the item stays out of sight until someone changes its status later), which is the right choice for almost every upload.

| Table              | Allowed values                                                       |
|--------------------|----------------------------------------------------------------------|
| `images.csv`       | `hidden` (default), `open`, `review_pending`, `finalized`, `deleted` |
| `candidates.csv`   | `hidden` (default), `open`, `no_overlap`, `has_overlap`, `deleted`   |
| `pairs.csv`        | `hidden` (default), `open`, `review_pending`, `finalized`, `deleted` |

## Full example

All nine example files shown on this page, together, form one complete, working upload. You can find them in [`zip-uploads-examples/`](zip-uploads-examples/):

- [`labels.csv`](zip-uploads-examples/labels.csv)
- [`cameras.csv`](zip-uploads-examples/cameras.csv)
- [`regions.csv`](zip-uploads-examples/regions.csv)
- [`dives.csv`](zip-uploads-examples/dives.csv)
- [`images.csv`](zip-uploads-examples/images.csv)
- [`candidates.csv`](zip-uploads-examples/candidates.csv)
- [`pairs.csv`](zip-uploads-examples/pairs.csv)
- [`helper_images.csv`](zip-uploads-examples/helper_images.csv)
- [`fun_facts.csv`](zip-uploads-examples/fun_facts.csv)
