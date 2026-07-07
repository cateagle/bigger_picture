import base64
import io
import os
import uuid

import pytest
from PIL import Image as PILImage


@pytest.fixture
def scientist(seed_user, login_as):
    user = seed_user(username="sci", role="scientist")
    login_as(user)
    return user


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _png_b64(width: int, height: int) -> str:
    img = PILImage.new("RGB", (width, height), (123, 50, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _make_region(client, title="reg") -> str:
    u = _new_uuid()
    resp = client.post("/api/v1/dataset/regions/create", json={"uuid": u, "title": title})
    assert resp.status_code == 201, resp.text
    return u


def _make_camera(client, title="cam") -> str:
    u = _new_uuid()
    resp = client.post("/api/v1/dataset/cameras/create", json={"uuid": u, "title": title})
    assert resp.status_code == 201, resp.text
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


def _create_image(client, dive, *, filepath, width=40, height=30, **extra):
    u = _new_uuid()
    body = {
        "uuid": u,
        "filename": os.path.basename(filepath),
        "filepath": filepath,
        "dive_uuid": dive,
        "image": _png_b64(width, height),
    }
    body.update(extra)
    resp = client.post("/api/v1/dataset/images/create", json=body)
    return u, resp


def test_create_image_happy_path(client, scientist, assets_dir):
    dive = _make_dive(client)
    u, resp = _create_image(client, dive, filepath="a/b/img1.png", width=64, height=48)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["uuid"] == u
    assert body["status"] == "hidden"
    assert body["size_x"] == 64
    assert body["size_y"] == 48
    assert body["dive"] == dive
    assert body["filename"] == "img1.png"
    assert body["filepath"] == "a/b/img1.png"
    assert body["created_by"] == str(uuid.UUID(bytes=scientist.uuid))
    # File landed under the app's assets dir.
    assert os.path.exists(os.path.join(assets_dir, "a", "b", "img1.png"))


def test_create_image_defaults_null(client, scientist):
    dive = _make_dive(client)
    _u, resp = _create_image(client, dive, filepath="plain.png")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["metadata"] is None
    assert body["difficulty"] is None
    assert body["priority"] is None


def test_create_image_traversal_filepath_is_422(client, scientist, assets_dir):
    dive = _make_dive(client)
    _u, resp = _create_image(client, dive, filepath="../evil.png")
    assert resp.status_code == 422, resp.text
    # No file written outside the assets dir.
    assert not os.path.exists(os.path.join(os.path.dirname(assets_dir), "evil.png"))
    # No row created.
    summary = client.get("/api/v1/dataset/summary").json()
    assert summary["image_count"] == 0


def test_create_image_unknown_dive_is_404(client, scientist):
    _u, resp = _create_image(client, _new_uuid(), filepath="x.png")
    assert resp.status_code == 404, resp.text


def test_create_image_malformed_uuid_is_422(client, scientist):
    dive = _make_dive(client)
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={
            "uuid": "not-a-uuid",
            "filename": "x.png",
            "filepath": "x.png",
            "dive_uuid": dive,
            "image": _png_b64(10, 10),
        },
    )
    assert resp.status_code == 422


def test_create_image_duplicate_filepath_is_409(client, scientist, assets_dir):
    dive = _make_dive(client)
    _u1, r1 = _create_image(client, dive, filepath="dup.png")
    assert r1.status_code == 201
    _u2, r2 = _create_image(client, dive, filepath="dup.png")
    assert r2.status_code == 409, r2.text
    # Original file still present (not unlinked by the failed second create).
    assert os.path.exists(os.path.join(assets_dir, "dup.png"))
    # Only one row exists.
    summary = client.get("/api/v1/dataset/summary").json()
    assert summary["image_count"] == 1


def test_create_image_undecodable_is_422(client, scientist):
    dive = _make_dive(client)
    # Valid base64 but not a real image.
    garbage = base64.b64encode(b"this is not an image").decode()
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={
            "uuid": _new_uuid(),
            "filename": "bad.png",
            "filepath": "bad.png",
            "dive_uuid": dive,
            "image": garbage,
        },
    )
    assert resp.status_code == 422, resp.text
    summary = client.get("/api/v1/dataset/summary").json()
    assert summary["image_count"] == 0


def test_update_filename_metadata_difficulty(client, scientist):
    dive = _make_dive(client)
    u, resp = _create_image(
        client, dive, filepath="u1.png", metadata={"a": 1}, difficulty=3
    )
    assert resp.status_code == 201
    # missing filename -> noop; explicit metadata value; explicit null difficulty -> clears
    resp = client.post(
        "/api/v1/dataset/images/update",
        json={"uuid": u, "filename": "renamed.png", "metadata": {"b": 2}, "difficulty": None},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["filename"] == "renamed.png"
    assert body["metadata"] == {"b": 2}
    assert body["difficulty"] is None


def test_update_missing_is_noop(client, scientist):
    dive = _make_dive(client)
    u, _ = _create_image(client, dive, filepath="keep.png", difficulty=7)
    resp = client.post("/api/v1/dataset/images/update", json={"uuid": u, "filename": "n.png"})
    assert resp.status_code == 200
    assert resp.json()["difficulty"] == 7


def test_update_new_image_changes_dimensions(client, scientist):
    dive = _make_dive(client)
    u, resp = _create_image(client, dive, filepath="dim.png", width=40, height=30)
    assert resp.json()["size_x"] == 40
    assert resp.json()["size_y"] == 30
    resp = client.post(
        "/api/v1/dataset/images/update",
        json={"uuid": u, "image": _png_b64(80, 90)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["size_x"] == 80
    assert body["size_y"] == 90


def test_update_unknown_uuid_is_404(client, scientist):
    resp = client.post(
        "/api/v1/dataset/images/update", json={"uuid": _new_uuid(), "filename": "x.png"}
    )
    assert resp.status_code == 404


def test_batch_status_change_happy(client, scientist):
    dive = _make_dive(client)
    u1, _ = _create_image(client, dive, filepath="b1.png")
    u2, _ = _create_image(client, dive, filepath="b2.png")
    u3, _ = _create_image(client, dive, filepath="b3.png")
    resp = client.post(
        "/api/v1/dataset/images/batch/status-change/open",
        json=[u1, u2, u3],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"updated": 3}
    # Verify each flipped to open.
    for u in (u1, u2, u3):
        r = client.post("/api/v1/dataset/images/update", json={"uuid": u})
        assert r.json()["status"] == "open"


def test_batch_status_change_unknown_status_is_422(client, scientist):
    dive = _make_dive(client)
    u1, _ = _create_image(client, dive, filepath="s1.png")
    resp = client.post(
        "/api/v1/dataset/images/batch/status-change/bogus",
        json=[u1],
    )
    assert resp.status_code == 422


def test_batch_status_change_missing_uuid_rolls_back(client, scientist):
    dive = _make_dive(client)
    u1, _ = _create_image(client, dive, filepath="r1.png")
    u2, _ = _create_image(client, dive, filepath="r2.png")
    # Put them at a known state first (finalized).
    resp = client.post(
        "/api/v1/dataset/images/batch/status-change/finalized",
        json=[u1, u2],
    )
    assert resp.status_code == 200
    # Now a batch with one missing uuid -> 404 and NOTHING changes.
    resp = client.post(
        "/api/v1/dataset/images/batch/status-change/open",
        json=[u1, _new_uuid(), u2],
    )
    assert resp.status_code == 404, resp.text
    for u in (u1, u2):
        r = client.post("/api/v1/dataset/images/update", json={"uuid": u})
        assert r.json()["status"] == "finalized"


def test_images_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann", role="annotator"))
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={
            "uuid": _new_uuid(),
            "filename": "x.png",
            "filepath": "x.png",
            "dive_uuid": _new_uuid(),
            "image": _png_b64(10, 10),
        },
    )
    assert resp.status_code == 403
