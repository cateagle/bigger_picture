import base64
import io
import os
import uuid

import pytest
from PIL import Image as PILImage


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _png_bytes(width: int, height: int, color=(123, 50, 200)) -> bytes:
    img = PILImage.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _png_b64(width: int, height: int, color=(123, 50, 200)) -> str:
    return base64.b64encode(_png_bytes(width, height, color)).decode()


def _make_region(client, title="reg") -> str:
    u = _new_uuid()
    assert client.post("/api/v1/dataset/regions/create", json={"uuid": u, "title": title}).status_code == 201
    return u


def _make_camera(client, title="cam") -> str:
    u = _new_uuid()
    assert client.post("/api/v1/dataset/cameras/create", json={"uuid": u, "title": title}).status_code == 201
    return u


def _make_dive(client, title="dive") -> str:
    region = _make_region(client, title=title + "-r")
    camera = _make_camera(client, title=title + "-c")
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": u, "title": title, "region": region, "camera": camera},
    )
    assert resp.status_code == 201, resp.text
    return u


def _create_image(client, dive, *, filepath, width=40, height=30, color=(123, 50, 200)) -> str:
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={
            "uuid": u,
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "dive_uuid": dive,
            "image": _png_b64(width, height, color),
        },
    )
    assert resp.status_code == 201, resp.text
    return u


@pytest.fixture
def scientist(client, seed_user, login_as):
    user = seed_user(username="sci", role="scientist", expert_level=5)
    login_as(user)
    return user


def _list_tmp_files(assets_dir) -> list[str]:
    tmp = os.path.join(assets_dir, ".tmp")
    if not os.path.isdir(tmp):
        return []
    return [f for f in os.listdir(tmp) if not f.startswith(".")]


# ------------------------- filepath move -------------------------


def test_update_filepath_moves_file(client, scientist, assets_dir):
    dive = _make_dive(client)
    original = _png_bytes(40, 30)
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={
            "uuid": u,
            "filename": "old.png",
            "filepath": "old/dir/old.png",
            "dive_uuid": dive,
            "image": base64.b64encode(original).decode(),
        },
    )
    assert resp.status_code == 201, resp.text
    old_path = os.path.join(assets_dir, "old", "dir", "old.png")
    assert os.path.exists(old_path)

    resp = client.post(
        "/api/v1/dataset/images/update",
        json={"uuid": u, "filepath": "new/dir/new.png"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["filepath"] == "new/dir/new.png"

    new_path = os.path.join(assets_dir, "new", "dir", "new.png")
    assert os.path.exists(new_path)
    assert not os.path.exists(old_path)
    with open(new_path, "rb") as fh:
        assert fh.read() == original


# ------------------------- new blob, same dims -------------------------


def test_update_blob_same_dims_swaps_content(client, scientist, assets_dir):
    dive = _make_dive(client)
    u = _create_image(client, dive, filepath="swap.png", width=40, height=30, color=(10, 20, 30))
    path = os.path.join(assets_dir, "swap.png")
    with open(path, "rb") as fh:
        before = fh.read()

    new_bytes = _png_bytes(40, 30, color=(200, 100, 50))
    resp = client.post(
        "/api/v1/dataset/images/update",
        json={"uuid": u, "image": base64.b64encode(new_bytes).decode()},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["size_x"] == 40
    assert body["size_y"] == 30
    with open(path, "rb") as fh:
        after = fh.read()
    assert after == new_bytes
    assert after != before
    assert _list_tmp_files(assets_dir) == []


# ------------------------- new blob, diff dims, no annotations -------------------------


def test_update_blob_diff_dims_no_annotations_ok(client, scientist, assets_dir):
    dive = _make_dive(client)
    u = _create_image(client, dive, filepath="grow.png", width=40, height=30)
    path = os.path.join(assets_dir, "grow.png")

    new_bytes = _png_bytes(80, 90)
    resp = client.post(
        "/api/v1/dataset/images/update",
        json={"uuid": u, "image": base64.b64encode(new_bytes).decode()},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["size_x"] == 80
    assert body["size_y"] == 90
    with open(path, "rb") as fh:
        assert fh.read() == new_bytes
    assert _list_tmp_files(assets_dir) == []


# ------------------------- new blob, diff dims, WITH annotation -> 409 -------------------------


def _open_pair(client, image_a, image_b):
    assert (
        client.post(
            "/api/v1/dataset/pairs/create",
            json={"image_a": image_a, "image_b": image_b},
        ).status_code
        == 201
    )
    resp = client.post(
        "/api/v1/dataset/pairs/batch/status-change/open",
        json=[{"image_a": image_a, "image_b": image_b}],
    )
    assert resp.status_code == 200, resp.text


def test_update_blob_diff_dims_with_annotation_is_409(client, scientist, assets_dir, seed_user, login_as):
    dive = _make_dive(client)
    u1 = _create_image(client, dive, filepath="ann1.png", width=40, height=30)
    u2 = _create_image(client, dive, filepath="ann2.png", width=40, height=30)
    _open_pair(client, u1, u2)

    # An annotator adds a point annotation on the pair involving u1.
    annotator = seed_user(username="ann", role="annotator", expert_level=1)
    login_as(annotator)
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": _new_uuid(), "image_a": u1, "image_b": u2, "x1": 1, "y1": 2, "x2": 3, "y2": 4},
    )
    assert resp.status_code == 201, resp.text

    # Back to the scientist to attempt a dimension-changing update.
    login_as(scientist)
    path = os.path.join(assets_dir, "ann1.png")
    with open(path, "rb") as fh:
        before = fh.read()

    resp = client.post(
        "/api/v1/dataset/images/update",
        json={"uuid": u1, "image": _png_b64(100, 100)},
    )
    assert resp.status_code == 409, resp.text

    # Nothing changed: DB dims unchanged, on-disk file is the original, no temp.
    check = client.post("/api/v1/dataset/images/update", json={"uuid": u1})
    assert check.json()["size_x"] == 40
    assert check.json()["size_y"] == 30
    with open(path, "rb") as fh:
        assert fh.read() == before
    assert _list_tmp_files(assets_dir) == []


def test_update_blob_same_dims_with_annotation_ok(client, scientist, assets_dir, seed_user, login_as):
    dive = _make_dive(client)
    u1 = _create_image(client, dive, filepath="ok1.png", width=40, height=30, color=(10, 20, 30))
    u2 = _create_image(client, dive, filepath="ok2.png", width=40, height=30)
    _open_pair(client, u1, u2)

    annotator = seed_user(username="ann2", role="annotator", expert_level=1)
    login_as(annotator)
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": _new_uuid(), "image_a": u1, "image_b": u2, "x1": 1, "y1": 2, "x2": 3, "y2": 4},
    )
    assert resp.status_code == 201, resp.text

    login_as(scientist)
    new_bytes = _png_bytes(40, 30, color=(9, 9, 9))
    resp = client.post(
        "/api/v1/dataset/images/update",
        json={"uuid": u1, "image": base64.b64encode(new_bytes).decode()},
    )
    assert resp.status_code == 200, resp.text
    with open(os.path.join(assets_dir, "ok1.png"), "rb") as fh:
        assert fh.read() == new_bytes


# ------------------------- filepath change + new blob together -------------------------


def test_update_filepath_and_blob_together(client, scientist, assets_dir):
    dive = _make_dive(client)
    u = _create_image(client, dive, filepath="both/old.png", width=40, height=30)
    old_path = os.path.join(assets_dir, "both", "old.png")
    assert os.path.exists(old_path)

    new_bytes = _png_bytes(40, 30, color=(1, 2, 3))
    resp = client.post(
        "/api/v1/dataset/images/update",
        json={
            "uuid": u,
            "filepath": "both/new.png",
            "image": base64.b64encode(new_bytes).decode(),
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["filepath"] == "both/new.png"

    new_path = os.path.join(assets_dir, "both", "new.png")
    assert not os.path.exists(old_path)
    assert os.path.exists(new_path)
    with open(new_path, "rb") as fh:
        assert fh.read() == new_bytes
    assert _list_tmp_files(assets_dir) == []


# ------------------------- traversal in new filepath -> 422 -------------------------


def test_update_traversal_filepath_is_422(client, scientist, assets_dir):
    dive = _make_dive(client)
    original = _png_bytes(40, 30)
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={
            "uuid": u,
            "filename": "trav.png",
            "filepath": "trav.png",
            "dive_uuid": dive,
            "image": base64.b64encode(original).decode(),
        },
    )
    assert resp.status_code == 201, resp.text
    path = os.path.join(assets_dir, "trav.png")

    resp = client.post(
        "/api/v1/dataset/images/update",
        json={"uuid": u, "filepath": "../evil.png"},
    )
    assert resp.status_code == 422, resp.text

    # Nothing moved; original intact; filepath unchanged; no escape file.
    assert os.path.exists(path)
    with open(path, "rb") as fh:
        assert fh.read() == original
    assert not os.path.exists(os.path.join(os.path.dirname(assets_dir), "evil.png"))
    check = client.post("/api/v1/dataset/images/update", json={"uuid": u})
    assert check.json()["filepath"] == "trav.png"
