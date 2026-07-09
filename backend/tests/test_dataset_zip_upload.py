import io
import os
import uuid
import zipfile
from pathlib import Path

import pytest
from blake3 import blake3
from PIL import Image as PILImage


@pytest.fixture
def scientist(seed_user, login_as):
    user = seed_user(username="sci", role="scientist")
    login_as(user)
    return user


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _png_bytes(width: int = 8, height: int = 6) -> bytes:
    img = PILImage.new("RGB", (width, height), (123, 50, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _build_zip(files: dict[str, bytes | str]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            zf.writestr(name, data)
    buf.seek(0)
    return buf


def _csv_row(*fields: str) -> str:
    return ";".join(fields) + "\n"


def _upload(client, files: dict[str, bytes | str]):
    zbuf = _build_zip(files)
    return client.post(
        "/api/v1/dataset/zip-upload",
        files={"file": ("fixture.zip", zbuf, "application/zip")},
    )


def _dataset_base_files(image_count: int = 3) -> tuple[dict[str, bytes | str], list[str], list[str]]:
    """Build regions/cameras/dives/images.csv + images/ for the image_source_a/b
    resolution tests below.

    Returns `(files, image_uuids, source_paths)` where `image_uuids[i]` is the
    uuid of the image whose `source_path` is `source_paths[i]`.
    """
    image_uuids = [_new_uuid() for _ in range(image_count)]
    source_paths = [f"img{i + 1}.png" for i in range(image_count)]
    images_rows = "".join(
        _csv_row(u, sp, "", "", "", "D1", "", "", "", "")
        for u, sp in zip(image_uuids, source_paths)
    )
    files: dict[str, bytes | str] = {
        "regions.csv": _csv_row("uuid", "title", "metadata", "description") + _csv_row("new", "R1", "", ""),
        "cameras.csv": _csv_row("uuid", "title", "metadata", "description") + _csv_row("new", "C1", "", ""),
        "dives.csv": (
            _csv_row(
                "uuid", "title", "metadata", "description",
                "region_uuid", "region_title", "camera_uuid", "camera_title",
            )
            + _csv_row("new", "D1", "", "", "", "R1", "", "C1")
        ),
        "images.csv": (
            _csv_row(
                "uuid", "source_path", "filename", "filepath",
                "dive_uuid", "dive_title", "status", "metadata", "difficulty", "priority",
            )
            + images_rows
        ),
    }
    for source_path in source_paths:
        files[f"images/{source_path}"] = _png_bytes()
    return files, image_uuids, source_paths


def test_zip_upload_happy_path_all_entities(client, scientist, assets_dir, import_dir):
    existing_camera_uuid = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/cameras/create",
        json={"uuid": existing_camera_uuid, "title": "Existing Camera"},
    )
    assert resp.status_code == 201, resp.text

    resp = _upload(
        client,
        {
            "labels.csv": (
                "uuid;scope;title;description\n"
                "new;point-annotation;Coral;A coral label\n"
            ),
            "regions.csv": (
                "uuid;title;metadata;description\n"
                "new;Gulf of Mexico;;A region\n"
            ),
            "cameras.csv": (
                "uuid;title;metadata;description\n"
                'new;GoPro Hero 11;{"iso": 100};\n'
            ),
            "dives.csv": (
                "uuid;title;metadata;description;region_uuid;region_title;camera_uuid;camera_title\n"
                f"new;Dive 1;;;;Gulf of Mexico;{existing_camera_uuid};\n"
                "new;Dive 2 No Camera;;;;Gulf of Mexico;;\n"
            ),
            "images.csv": (
                "uuid;source_path;filename;filepath;dive_uuid;dive_title;status;metadata;difficulty;priority\n"
                "new;img1.png;;;;Dive 1;;;;\n"
                "new;img2.png;shown.png;custom/path.png;;Dive 1;open;;3;7\n"
            ),
            "images/img1.png": _png_bytes(),
            "images/img2.png": _png_bytes(),
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body == {
        "created": {
            "labels": 1,
            "cameras": 1,
            "regions": 1,
            "dives": 2,
            "images": 2,
            "candidate_pairs": 0,
            "image_pairs": 0,
            "helper_images": 0,
            "fun_facts": 0,
        }
    }

    summary = client.get("/api/v1/dataset/summary").json()
    assert summary["dive_count"] == 2
    assert summary["image_count"] == 2

    dives = client.get("/api/v1/dataset/dives").json()["dives"]
    dive1 = next(d for d in dives if d["title"] == "Dive 1")
    assert dive1["camera"] == existing_camera_uuid
    dive2 = next(d for d in dives if d["title"] == "Dive 2 No Camera")
    assert dive2["camera"] == "0484f929-b38d-4076-8aea-864e9c2138a2"

    # img1 used the default filepath fallback: "{dive_uuid}/{image_uuid}.png"
    dive1_dir = os.path.join(assets_dir, dive1["uuid"])
    assert os.path.isdir(dive1_dir)
    assert len(os.listdir(dive1_dir)) == 1
    # img2 used the explicit filepath.
    assert os.path.isfile(os.path.join(assets_dir, "custom", "path.png"))

    assert os.listdir(import_dir) == []


def test_zip_upload_response_has_no_minted_uuids(client, scientist):
    resp = _upload(
        client,
        {"regions.csv": "uuid;title;metadata;description\nnew;Some Region;;\n"},
    )
    assert resp.status_code == 201, resp.text
    assert set(resp.json().keys()) == {"created"}
    assert set(resp.json()["created"].keys()) == {
        "labels", "cameras", "regions", "dives", "images", "candidate_pairs", "image_pairs",
        "helper_images", "fun_facts",
    }


def test_zip_upload_missing_referenced_entity(client, scientist, import_dir):
    resp = _upload(
        client,
        {
            "dives.csv": (
                "uuid;title;metadata;description;region_uuid;region_title;camera_uuid;camera_title\n"
                f"new;Orphan Dive;;;{_new_uuid()};;;\n"
            ),
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "dives.csv"
    assert detail["row"] == 2

    summary = client.get("/api/v1/dataset/summary").json()
    assert summary["dive_count"] == 0
    assert os.listdir(import_dir) == []


def test_zip_upload_duplicate_title_conflict(client, scientist):
    resp = _upload(
        client,
        {
            "regions.csv": (
                "uuid;title;metadata;description\n"
                "new;Duplicate Region;;\n"
                "new;Duplicate Region;;\n"
            ),
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "regions.csv"
    assert detail["row"] == 3

    resp = client.get("/api/v1/dataset/dives")
    assert resp.status_code == 200


def test_zip_upload_invalid_image_data(client, scientist, assets_dir):
    resp = _upload(
        client,
        {
            "regions.csv": "uuid;title;metadata;description\nnew;R1;;\n",
            "cameras.csv": "uuid;title;metadata;description\nnew;C1;;\n",
            "dives.csv": (
                "uuid;title;metadata;description;region_uuid;region_title;camera_uuid;camera_title\n"
                "new;D1;;;;R1;;C1\n"
            ),
            "images.csv": (
                "uuid;source_path;filename;filepath;dive_uuid;dive_title;status;metadata;difficulty;priority\n"
                "new;bad.png;;;;D1;;;;\n"
            ),
            "images/bad.png": b"not a real image",
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "images.csv"

    summary = client.get("/api/v1/dataset/summary").json()
    assert summary["dive_count"] == 0
    assert summary["image_count"] == 0
    for root, _dirs, files in os.walk(assets_dir):
        assert files == []


def test_zip_upload_zip_slip_rejected(client, scientist, tmp_path):
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr(zipfile.ZipInfo("../evil.txt"), b"pwned")
    zbuf.seek(0)
    resp = client.post(
        "/api/v1/dataset/zip-upload",
        files={"file": ("fixture.zip", zbuf, "application/zip")},
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "<zip>"

    for root, _dirs, files in os.walk(tmp_path):
        assert "evil.txt" not in files


def test_zip_upload_images_csv_without_images_folder(client, scientist):
    resp = _upload(
        client,
        {
            "regions.csv": "uuid;title;metadata;description\nnew;R1;;\n",
            "cameras.csv": "uuid;title;metadata;description\nnew;C1;;\n",
            "dives.csv": (
                "uuid;title;metadata;description;region_uuid;region_title;camera_uuid;camera_title\n"
                "new;D1;;;;R1;;C1\n"
            ),
            "images.csv": (
                "uuid;source_path;filename;filepath;dive_uuid;dive_title;status;metadata;difficulty;priority\n"
                "new;missing.png;;;;D1;;;;\n"
            ),
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "images.csv"
    assert "images/" in detail["reason"]


def test_zip_upload_malformed_difficulty(client, scientist):
    resp = _upload(
        client,
        {
            "regions.csv": "uuid;title;metadata;description\nnew;R1;;\n",
            "cameras.csv": "uuid;title;metadata;description\nnew;C1;;\n",
            "dives.csv": (
                "uuid;title;metadata;description;region_uuid;region_title;camera_uuid;camera_title\n"
                "new;D1;;;;R1;;C1\n"
            ),
            "images.csv": (
                "uuid;source_path;filename;filepath;dive_uuid;dive_title;status;metadata;difficulty;priority\n"
                "new;img1.png;;;;D1;;;not-a-number;\n"
            ),
            "images/img1.png": _png_bytes(),
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "images.csv"
    assert "difficulty" in detail["reason"]


def test_zip_upload_cross_dive_pair_rejected(client, scientist):
    region = _new_uuid()
    assert client.post(
        "/api/v1/dataset/regions/create", json={"uuid": region, "title": "R"}
    ).status_code == 201
    camera = _new_uuid()
    assert client.post(
        "/api/v1/dataset/cameras/create", json={"uuid": camera, "title": "C"}
    ).status_code == 201
    dive_a = _new_uuid()
    assert client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": dive_a, "title": "Dive A", "region": region, "camera": camera},
    ).status_code == 201
    dive_b = _new_uuid()
    assert client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": dive_b, "title": "Dive B", "region": region, "camera": camera},
    ).status_code == 201

    image_a = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={
            "uuid": image_a,
            "filename": "a.png",
            "filepath": "a/a.png",
            "dive_uuid": dive_a,
            "image": __import__("base64").b64encode(_png_bytes()).decode(),
        },
    )
    assert resp.status_code == 201, resp.text
    image_b = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={
            "uuid": image_b,
            "filename": "b.png",
            "filepath": "b/b.png",
            "dive_uuid": dive_b,
            "image": __import__("base64").b64encode(_png_bytes()).decode(),
        },
    )
    assert resp.status_code == 201, resp.text

    resp = _upload(
        client,
        {"candidates.csv": f"image_a;image_b;status\n{image_a};{image_b};\n"},
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "candidates.csv"
    # Both images are pre-existing (not part of this import's images.csv), so
    # the error must describe them by their server-side filepath/filename.
    assert "filepath 'a/a.png'" in detail["reason"]
    assert "filepath 'b/b.png'" in detail["reason"]

    resp = client.get("/api/v1/dataset/summary")
    assert resp.status_code == 200


def test_zip_upload_all_or_nothing_rollback(client, scientist, import_dir):
    resp = _upload(
        client,
        {
            "labels.csv": "uuid;scope;title;description\nnew;s;Coral;\n",
            "regions.csv": "uuid;title;metadata;description\nnew;R1;;\n",
            "cameras.csv": "uuid;title;metadata;description\nnew;C1;;\n",
            "dives.csv": (
                "uuid;title;metadata;description;region_uuid;region_title;camera_uuid;camera_title\n"
                "new;D1;;;;R1;;C1\n"
            ),
            "images.csv": (
                "uuid;source_path;filename;filepath;dive_uuid;dive_title;status;metadata;difficulty;priority\n"
                "new;missing.png;;;;D1;;;;\n"
            ),
            "images/present.png": _png_bytes(),
        },
    )
    assert resp.status_code == 422, resp.text

    summary = client.get("/api/v1/dataset/summary").json()
    assert summary["dive_count"] == 0
    assert summary["image_count"] == 0

    resp = client.get("/api/v1/dataset/dives")
    assert resp.json()["dives"] == []

    assert os.listdir(import_dir) == []


def test_zip_upload_requires_scientist_role(client, seed_user, login_as):
    user = seed_user(username="ann", role="annotator")
    login_as(user)
    resp = _upload(client, {"regions.csv": "uuid;title;metadata;description\nnew;R1;;\n"})
    assert resp.status_code == 403


def test_zip_upload_helper_images_and_fun_facts_happy_path(client, scientist, assets_dir):
    hi1_uuid = _new_uuid()
    hi2_uuid = _new_uuid()
    img_bytes_1 = _png_bytes(width=8, height=6)
    img_bytes_2 = _png_bytes(width=10, height=10)

    resp = _upload(
        client,
        {
            "regions.csv": (
                _csv_row("uuid", "title", "metadata", "description")
                + _csv_row("new", "R1", "", "")
            ),
            "helper_images.csv": (
                _csv_row("uuid", "source_path", "filename", "filepath")
                + _csv_row(hi1_uuid, "img1.png", "", "")
                + _csv_row(hi2_uuid, "img2.png", "", "custom/helper.png")
            ),
            "helper_images/img1.png": img_bytes_1,
            "helper_images/img2.png": img_bytes_2,
            "fun_facts.csv": (
                _csv_row("uuid", "title", "fact", "min_level", "region_uuid", "region_title", "image_uuid")
                + _csv_row("new", "Fact One", '{"body": "hi"}', "", "", "R1", hi1_uuid)
                + _csv_row("new", "Fact Two", '{"body": "bye"}', "", "", "", "")
            ),
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created"]["helper_images"] == 2
    assert body["created"]["fun_facts"] == 2

    expected_hash = blake3(img_bytes_1).hexdigest()
    assert os.path.isfile(os.path.join(assets_dir, "helper_images", f"{expected_hash}.png"))
    assert os.path.isfile(os.path.join(assets_dir, "custom", "helper.png"))

    helper_images = client.get("/api/v1/dataset/helper-images").json()
    assert helper_images["total"] == 2

    fun_facts = client.get("/api/v1/dataset/fun-facts").json()["fun_facts"]
    assert len(fun_facts) == 2
    fact_two = next(f for f in fun_facts if f["title"] == "Fact Two")
    assert fact_two["min_level"] == 0
    assert fact_two["region"] is None
    assert fact_two["image"] is None
    fact_one = next(f for f in fun_facts if f["title"] == "Fact One")
    assert fact_one["image"]["filename"] == "img1.png"


def test_zip_upload_helper_images_csv_without_folder(client, scientist):
    resp = _upload(
        client,
        {
            "helper_images.csv": (
                _csv_row("uuid", "source_path", "filename", "filepath")
                + _csv_row("new", "missing.png", "", "")
            ),
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "helper_images.csv"
    assert "helper_images/" in detail["reason"]


def test_zip_upload_invalid_helper_image_data(client, scientist, assets_dir, import_dir):
    resp = _upload(
        client,
        {
            "helper_images.csv": (
                _csv_row("uuid", "source_path", "filename", "filepath")
                + _csv_row("new", "bad.png", "", "")
            ),
            "helper_images/bad.png": b"not a real image",
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "helper_images.csv"

    for root, _dirs, files in os.walk(assets_dir):
        assert files == []
    assert os.listdir(import_dir) == []


def test_zip_upload_fun_fact_blank_fact_required(client, scientist):
    resp = _upload(
        client,
        {
            "fun_facts.csv": (
                _csv_row("uuid", "title", "fact", "min_level", "region_uuid", "region_title", "image_uuid")
                + _csv_row("new", "Fact", "", "", "", "", "")
            ),
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "fun_facts.csv"
    assert "fact" in detail["reason"]


def test_zip_upload_fun_fact_missing_region_reference(client, scientist):
    resp = _upload(
        client,
        {
            "fun_facts.csv": (
                _csv_row("uuid", "title", "fact", "min_level", "region_uuid", "region_title", "image_uuid")
                + _csv_row("new", "Fact", '{"body": "x"}', "", _new_uuid(), "", "")
            ),
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "fun_facts.csv"


def test_zip_upload_fun_fact_missing_image_reference(client, scientist):
    resp = _upload(
        client,
        {
            "fun_facts.csv": (
                _csv_row("uuid", "title", "fact", "min_level", "region_uuid", "region_title", "image_uuid")
                + _csv_row("new", "Fact", '{"body": "x"}', "", "", "", _new_uuid())
            ),
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "fun_facts.csv"


def test_zip_upload_fun_fact_duplicate_title_conflict(client, scientist):
    resp = _upload(
        client,
        {
            "fun_facts.csv": (
                _csv_row("uuid", "title", "fact", "min_level", "region_uuid", "region_title", "image_uuid")
                + _csv_row("new", "Dup", '{"body": "x"}', "", "", "", "")
                + _csv_row("new", "Dup", '{"body": "y"}', "", "", "", "")
            ),
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "fun_facts.csv"
    assert detail["row"] == 3


def test_zip_upload_helper_images_rollback_on_later_fun_facts_failure(client, scientist, assets_dir, import_dir):
    resp = _upload(
        client,
        {
            "helper_images.csv": (
                _csv_row("uuid", "source_path", "filename", "filepath")
                + _csv_row("new", "img1.png", "", "")
            ),
            "helper_images/img1.png": _png_bytes(),
            "fun_facts.csv": (
                _csv_row("uuid", "title", "fact", "min_level", "region_uuid", "region_title", "image_uuid")
                + _csv_row("new", "Dup", '{"body": "x"}', "", "", "", "")
                + _csv_row("new", "Dup", '{"body": "y"}', "", "", "", "")
            ),
        },
    )
    assert resp.status_code == 422, resp.text

    helper_images = client.get("/api/v1/dataset/helper-images").json()
    assert helper_images["total"] == 0

    assert os.listdir(import_dir) == []
    helper_images_dir = os.path.join(assets_dir, "helper_images")
    assert not os.path.isdir(helper_images_dir) or os.listdir(helper_images_dir) == []


def test_zip_upload_pair_image_source_columns(client, scientist):
    files, image_uuids, source_paths = _dataset_base_files(3)
    img1_uuid, img2_uuid, img3_uuid = image_uuids
    img1_src, img2_src, img3_src = source_paths

    files["candidates.csv"] = (
        _csv_row("image_a", "image_b", "image_source_a", "image_source_b", "status")
        # Row 1: resolved purely by source_path (both uuids left blank).
        + _csv_row("", "", img1_src, img2_src, "")
        # Row 2: mixed - image_a by uuid, image_b by source_path.
        + _csv_row(img1_uuid, "", "", img3_src, "has_overlap")
        # Row 3: image_a has both uuid and a bogus source_path - uuid must win.
        + _csv_row(img2_uuid, img3_uuid, "does-not-exist.png", "", "")
    )
    resp = _upload(client, files)
    assert resp.status_code == 201, resp.text
    assert resp.json()["created"]["candidate_pairs"] == 3


def test_zip_upload_pair_source_not_in_images_csv(client, scientist):
    files, image_uuids, _source_paths = _dataset_base_files(2)
    files["candidates.csv"] = (
        _csv_row("image_a", "image_b", "image_source_a", "image_source_b", "status")
        + _csv_row("", image_uuids[1], "missing.png", "", "")
    )
    resp = _upload(client, files)
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "candidates.csv"
    assert "image_source_a" in detail["reason"]
    assert "missing.png" in detail["reason"]


def test_zip_upload_pair_missing_both_uuid_and_source(client, scientist):
    files, image_uuids, _source_paths = _dataset_base_files(2)
    files["candidates.csv"] = (
        _csv_row("image_a", "image_b", "image_source_a", "image_source_b", "status")
        + _csv_row(image_uuids[0], "", "", "", "")
    )
    resp = _upload(client, files)
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "candidates.csv"
    assert "image_b" in detail["reason"]
    assert "image_source_b" in detail["reason"]


def test_zip_upload_pair_same_image_error_includes_source_path(client, scientist):
    files, _image_uuids, source_paths = _dataset_base_files(1)
    files["candidates.csv"] = (
        _csv_row("image_a", "image_b", "image_source_a", "image_source_b", "status")
        + _csv_row("", "", source_paths[0], source_paths[0], "")
    )
    resp = _upload(client, files)
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["file"] == "candidates.csv"
    assert "must differ" in detail["reason"]
    assert f"source_path {source_paths[0]!r}" in detail["reason"]


def test_zip_upload_full_documented_example_works(client, scientist):
    """The CSVs shipped under docs/zip-uploads-examples/ are advertised in
    docs/zip-upload.md as forming one complete, working upload - verify that
    claim stays true as the format evolves."""
    examples_dir = Path(__file__).resolve().parents[2] / "docs" / "zip-uploads-examples"
    files: dict[str, bytes | str] = {}
    for csv_file in examples_dir.glob("*.csv"):
        files[csv_file.name] = csv_file.read_bytes()

    # images.csv references images/dive-a/frame_000{1,2,3}.jpg, images/dive-b/frame_0001.jpg,
    # images/dive-c/frame_000{1,2}.jpg (see docs/zip-upload.md's images.csv example).
    for rel in [
        "dive-a/frame_0001.jpg", "dive-a/frame_0002.jpg", "dive-a/frame_0003.jpg",
        "dive-b/frame_0001.jpg",
        "dive-c/frame_0001.jpg", "dive-c/frame_0002.jpg",
    ]:
        files[f"images/{rel}"] = _png_bytes()
    # helper_images.csv references helper_images/{jellyfish.jpg,anglerfish.jpg,coral-icon.png}.
    # Distinct sizes so their content-addressed filepaths don't collide.
    for i, rel in enumerate(["jellyfish.jpg", "anglerfish.jpg", "coral-icon.png"]):
        files[f"helper_images/{rel}"] = _png_bytes(width=8 + i, height=6 + i)

    resp = _upload(client, files)
    assert resp.status_code == 201, resp.text
    assert resp.json()["created"] == {
        "labels": 2,
        "cameras": 2,
        "regions": 2,
        "dives": 3,
        "images": 6,
        "candidate_pairs": 3,
        "image_pairs": 3,
        "helper_images": 3,
        "fun_facts": 3,
    }
