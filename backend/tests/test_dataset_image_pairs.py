import base64
import io
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


def _png_b64(width=10, height=10) -> str:
    img = PILImage.new("RGB", (width, height), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _make_dive(client, title="dive") -> str:
    region = _new_uuid()
    assert client.post(
        "/api/v1/dataset/regions/create", json={"uuid": region, "title": title + "-r"}
    ).status_code == 201
    camera = _new_uuid()
    assert client.post(
        "/api/v1/dataset/cameras/create", json={"uuid": camera, "title": title + "-c"}
    ).status_code == 201
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": u, "title": title, "region": region, "camera": camera},
    )
    assert resp.status_code == 201, resp.text
    return u


def _make_image(client, dive, filepath) -> str:
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={
            "uuid": u,
            "filename": filepath,
            "filepath": filepath,
            "dive_uuid": dive,
            "image": _png_b64(),
        },
    )
    assert resp.status_code == 201, resp.text
    return u


@pytest.fixture
def images(client, scientist):
    dive = _make_dive(client)
    return [_make_image(client, dive, f"img{i}.png") for i in range(4)]


def test_create_pair_happy_sorted_and_hidden(client, images, scientist):
    resp = client.post(
        "/api/v1/dataset/pairs/create",
        json={"image_a": images[0], "image_b": images[1]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "hidden"
    assert body["created_by"] == str(uuid.UUID(bytes=scientist.uuid))
    assert body["difficulty"] is None
    assert body["priority"] is None
    assert {body["image_a"], body["image_b"]} == {images[0], images[1]}


def test_create_pair_duplicate_is_409(client, images):
    assert client.post(
        "/api/v1/dataset/pairs/create",
        json={"image_a": images[0], "image_b": images[1]},
    ).status_code == 201
    resp = client.post(
        "/api/v1/dataset/pairs/create",
        json={"image_a": images[1], "image_b": images[0]},
    )
    assert resp.status_code == 409, resp.text


def test_create_pair_missing_image_is_404(client, images):
    resp = client.post(
        "/api/v1/dataset/pairs/create",
        json={"image_a": images[0], "image_b": _new_uuid()},
    )
    assert resp.status_code == 404, resp.text


def test_create_pair_same_image_is_422(client, images):
    resp = client.post(
        "/api/v1/dataset/pairs/create",
        json={"image_a": images[0], "image_b": images[0]},
    )
    assert resp.status_code == 422, resp.text


def test_batch_status_change_open(client, images):
    for pair in [(0, 1), (1, 2)]:
        assert client.post(
            "/api/v1/dataset/pairs/create",
            json={"image_a": images[pair[0]], "image_b": images[pair[1]]},
        ).status_code == 201
    resp = client.post(
        "/api/v1/dataset/pairs/batch/status-change/open",
        json=[
            {"image_a": images[0], "image_b": images[1]},
            {"image_a": images[1], "image_b": images[2]},
        ],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"updated": 2}


def test_batch_unknown_status_is_422(client, images):
    assert client.post(
        "/api/v1/dataset/pairs/create",
        json={"image_a": images[0], "image_b": images[1]},
    ).status_code == 201
    resp = client.post(
        "/api/v1/dataset/pairs/batch/status-change/bogus",
        json=[{"image_a": images[0], "image_b": images[1]}],
    )
    assert resp.status_code == 422, resp.text


def test_batch_missing_pair_rolls_back(client, images):
    assert client.post(
        "/api/v1/dataset/pairs/create",
        json={"image_a": images[0], "image_b": images[1]},
    ).status_code == 201
    resp = client.post(
        "/api/v1/dataset/pairs/batch/status-change/open",
        json=[
            {"image_a": images[0], "image_b": images[1]},
            {"image_a": images[2], "image_b": images[3]},
        ],
    )
    assert resp.status_code == 404, resp.text
    ok = client.post(
        "/api/v1/dataset/pairs/batch/status-change/open",
        json=[{"image_a": images[0], "image_b": images[1]}],
    )
    assert ok.status_code == 200


def test_pairs_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann", role="annotator"))
    resp = client.post(
        "/api/v1/dataset/pairs/create",
        json={"image_a": _new_uuid(), "image_b": _new_uuid()},
    )
    assert resp.status_code == 403
