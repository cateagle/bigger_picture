import io
import os
import uuid
import zipfile

import pytest
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


def _upload(client, files: dict[str, bytes | str]):
    zbuf = _build_zip(files)
    return client.post(
        "/api/v1/dataset/zip-upload",
        files={"file": ("fixture.zip", zbuf, "application/zip")},
    )


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
