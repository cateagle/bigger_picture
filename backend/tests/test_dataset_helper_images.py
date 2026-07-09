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


def _png_b64(color) -> str:
    img = PILImage.new("RGB", (10, 10), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _create_fact_with_image(client, *, title: str, color) -> None:
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={
            "uuid": _new_uuid(), "title": title, "fact": {},
            "image": _png_b64(color), "image_filename": f"{title}.png",
        },
    )
    assert resp.status_code == 201, resp.text


def test_list_helper_images_paginates(client, scientist):
    for i in range(5):
        _create_fact_with_image(client, title=f"fact-{i}", color=(i * 40, i * 30, i * 20))

    resp = client.get("/api/v1/dataset/helper-images?page=1&page_size=2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["helper_images"]) == 2
    assert body["total"] == 5

    resp2 = client.get("/api/v1/dataset/helper-images?page=3&page_size=2")
    assert len(resp2.json()["helper_images"]) == 1


def test_list_helper_images_dedup_does_not_inflate_total(client, scientist):
    b64 = _png_b64((1, 2, 3))
    for title in ("a", "b"):
        resp = client.post(
            "/api/v1/dataset/fun-facts/create",
            json={"uuid": _new_uuid(), "title": title, "fact": {}, "image": b64, "image_filename": f"{title}.png"},
        )
        assert resp.status_code == 201, resp.text

    resp = client.get("/api/v1/dataset/helper-images")
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1


def test_list_helper_images_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann", role="annotator"))
    resp = client.get("/api/v1/dataset/helper-images")
    assert resp.status_code == 403
