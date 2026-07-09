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


def _png_b64(width: int = 10, height: int = 10, color=(123, 50, 200)) -> str:
    img = PILImage.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _jpeg_b64(width: int = 10, height: int = 10, color=(10, 200, 30)) -> str:
    img = PILImage.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def test_create_fun_fact_happy_path(client, scientist):
    u = _new_uuid()
    fact = {"text": "Octopuses have three hearts."}
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "octopus hearts", "fact": fact, "min_level": 2},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["uuid"] == u
    assert body["title"] == "octopus hearts"
    assert body["fact"] == fact
    assert body["min_level"] == 2
    assert body["region"] is None
    assert body["created_by"] == str(uuid.UUID(bytes=scientist.uuid))


def test_create_fun_fact_defaults(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "default fact", "fact": {"text": "hi"}},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["min_level"] == 0
    assert body["region"] is None


def test_create_fun_fact_with_region(client, scientist):
    region = _new_uuid()
    assert client.post(
        "/api/v1/dataset/regions/create", json={"uuid": region, "title": "gulf"}
    ).status_code == 201

    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "gulf fact", "fact": {"text": "hi"}, "region": region},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["region"] == region


def test_create_fun_fact_unknown_region_is_404(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "orphan fact", "fact": {}, "region": _new_uuid()},
    )
    assert resp.status_code == 404


def test_create_fun_fact_unique_title_conflicts(client, scientist):
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "dup", "fact": {}},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "dup", "fact": {}},
    )
    assert resp.status_code == 409


def test_update_fields(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "before", "fact": {"a": 1}, "min_level": 0},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "title": "after", "fact": {"a": 2}, "min_level": 4},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "after"
    assert body["fact"] == {"a": 2}
    assert body["min_level"] == 4


def test_update_explicit_null_on_title_fact_min_level_is_noop(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "keep", "fact": {"a": 1}, "min_level": 3},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "title": None, "fact": None, "min_level": None},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "keep"
    assert body["fact"] == {"a": 1}
    assert body["min_level"] == 3


def test_update_sets_region(client, scientist):
    region = _new_uuid()
    client.post("/api/v1/dataset/regions/create", json={"uuid": region, "title": "north"})
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "regionless", "fact": {}},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "region": region},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["region"] == region


def test_update_explicit_null_clears_region(client, scientist):
    region = _new_uuid()
    client.post("/api/v1/dataset/regions/create", json={"uuid": region, "title": "south"})
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "regioned", "fact": {}, "region": region},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "region": None},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["region"] is None


def test_update_unknown_uuid_is_404(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/update", json={"uuid": _new_uuid(), "title": "x"}
    )
    assert resp.status_code == 404


def test_list_paginates(client, scientist):
    for i in range(5):
        client.post(
            "/api/v1/dataset/fun-facts/create",
            json={"uuid": _new_uuid(), "title": f"fact-{i}", "fact": {}},
        )
    resp = client.get("/api/v1/dataset/fun-facts?page=1&page_size=2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["fun_facts"]) == 2
    assert body["total"] == 5

    resp2 = client.get("/api/v1/dataset/fun-facts?page=3&page_size=2")
    assert len(resp2.json()["fun_facts"]) == 1


def test_fun_facts_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann", role="annotator"))
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "t", "fact": {}},
    )
    assert resp.status_code == 403


def test_create_fun_fact_with_image_upload(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={
            "uuid": _new_uuid(), "title": "with image", "fact": {},
            "image": _png_b64(), "image_filename": "cool.png",
        },
    )
    assert resp.status_code == 201, resp.text
    image = resp.json()["image"]
    assert image is not None
    assert image["filepath"].startswith("helper_images/")
    assert image["filepath"].endswith(".png")
    assert image["filename"] == "cool.png"


def test_create_fun_fact_image_dedup(client, scientist):
    b64 = _png_b64()
    resp1 = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "first", "fact": {}, "image": b64, "image_filename": "first.png"},
    )
    resp2 = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "second", "fact": {}, "image": b64, "image_filename": "second.png"},
    )
    assert resp1.status_code == 201, resp1.text
    assert resp2.status_code == 201, resp2.text
    image1 = resp1.json()["image"]
    image2 = resp2.json()["image"]
    assert image1["uuid"] == image2["uuid"]
    assert image1["filepath"] == image2["filepath"]
    # dedup reuses the original row, so the second upload's filename is discarded.
    assert image1["filename"] == "first.png"
    assert image2["filename"] == "first.png"


def test_create_fun_fact_image_jpeg_extension(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={
            "uuid": _new_uuid(), "title": "jpeg fact", "fact": {},
            "image": _jpeg_b64(), "image_filename": "photo.jpg",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["image"]["filepath"].endswith(".jpg")


def test_create_fun_fact_image_and_image_uuid_mutually_exclusive(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={
            "uuid": _new_uuid(), "title": "conflict", "fact": {},
            "image": _png_b64(), "image_filename": "a.png", "image_uuid": _new_uuid(),
        },
    )
    assert resp.status_code == 422


def test_create_fun_fact_image_without_filename_is_422(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "no filename", "fact": {}, "image": _png_b64()},
    )
    assert resp.status_code == 422


def test_create_fun_fact_filename_without_image_is_422(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "dangling filename", "fact": {}, "image_filename": "a.png"},
    )
    assert resp.status_code == 422


def test_create_fun_fact_with_image_uuid_reference(client, scientist):
    first = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "source", "fact": {}, "image": _png_b64(), "image_filename": "src.png"},
    )
    image_uuid = first.json()["image"]["uuid"]

    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "referrer", "fact": {}, "image_uuid": image_uuid},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["image"]["uuid"] == image_uuid


def test_create_fun_fact_unknown_image_uuid_is_404(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "orphan image", "fact": {}, "image_uuid": _new_uuid()},
    )
    assert resp.status_code == 404


def test_create_fun_fact_undecodable_image_is_422(client, scientist):
    garbage = base64.b64encode(b"not an image").decode()
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "bad image", "fact": {}, "image": garbage, "image_filename": "bad.png"},
    )
    assert resp.status_code == 422


def test_update_fun_fact_uploads_image(client, scientist):
    u = _new_uuid()
    client.post("/api/v1/dataset/fun-facts/create", json={"uuid": u, "title": "no image yet", "fact": {}})
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "image": _png_b64(), "image_filename": "added.png"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["image"]["filename"] == "added.png"


def test_update_fun_fact_references_existing_image(client, scientist):
    source = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "src2", "fact": {}, "image": _png_b64(), "image_filename": "src2.png"},
    )
    image_uuid = source.json()["image"]["uuid"]

    u = _new_uuid()
    client.post("/api/v1/dataset/fun-facts/create", json={"uuid": u, "title": "referrer2", "fact": {}})
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "image_uuid": image_uuid},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["image"]["uuid"] == image_uuid


def test_update_fun_fact_unknown_image_uuid_is_404(client, scientist):
    u = _new_uuid()
    client.post("/api/v1/dataset/fun-facts/create", json={"uuid": u, "title": "unknown ref", "fact": {}})
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "image_uuid": _new_uuid()},
    )
    assert resp.status_code == 404


def test_update_fun_fact_clear_image(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "clearable", "fact": {}, "image": _png_b64(), "image_filename": "clear.png"},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "clear_image": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["image"] is None


def test_update_fun_fact_omitted_image_fields_is_noop(client, scientist):
    u = _new_uuid()
    create_resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "untouched", "fact": {}, "image": _png_b64(), "image_filename": "keep.png"},
    )
    image_uuid = create_resp.json()["image"]["uuid"]

    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "title": "still untouched"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["image"]["uuid"] == image_uuid


def test_update_fun_fact_image_uuid_and_clear_image_mutually_exclusive(client, scientist):
    u = _new_uuid()
    client.post("/api/v1/dataset/fun-facts/create", json={"uuid": u, "title": "combo", "fact": {}})
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "image_uuid": _new_uuid(), "clear_image": True},
    )
    assert resp.status_code == 422


def test_update_fun_fact_image_and_clear_image_mutually_exclusive(client, scientist):
    u = _new_uuid()
    client.post("/api/v1/dataset/fun-facts/create", json={"uuid": u, "title": "combo2", "fact": {}})
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "image": _png_b64(), "image_filename": "x.png", "clear_image": True},
    )
    assert resp.status_code == 422
