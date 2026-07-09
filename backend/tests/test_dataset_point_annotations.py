import base64
import csv
import io
import uuid

import pytest
from PIL import Image as PILImage


@pytest.fixture
def scientist(seed_user, login_as):
    user = seed_user(username="sci", role="scientist", expert_level=5)
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


def _open_pair(client, image_a, image_b):
    assert client.post(
        "/api/v1/dataset/pairs/create", json={"image_a": image_a, "image_b": image_b}
    ).status_code == 201
    resp = client.post(
        "/api/v1/dataset/pairs/batch/status-change/open",
        json=[{"image_a": image_a, "image_b": image_b}],
    )
    assert resp.status_code == 200, resp.text


def _create_annotation(client, image_a, image_b, x1=1, y1=2, x2=3, y2=4) -> str:
    u = _new_uuid()
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": u, "image_a": image_a, "image_b": image_b, "x1": x1, "y1": y1, "x2": x2, "y2": y2},
    )
    assert resp.status_code == 201, resp.text
    return u


def test_list_annotations_returns_annotations_in_dive(client, scientist, seed_user, login_as):
    dive = _make_dive(client)
    a = _make_image(client, dive, "la.png")
    b = _make_image(client, dive, "lb.png")
    _open_pair(client, a, b)

    login_as(seed_user(username="ann", role="annotator", expert_level=2))
    u1 = _create_annotation(client, a, b, x1=1, y1=1, x2=2, y2=2)
    u2 = _create_annotation(client, a, b, x1=3, y1=3, x2=4, y2=4)

    login_as(scientist)
    resp = client.get(f"/api/v1/dataset/annotations?dive={dive}")
    assert resp.status_code == 200, resp.text
    annotations = resp.json()["annotations"]
    assert {item["uuid"] for item in annotations} == {u1, u2}
    assert all({item["image_a"], item["image_b"]} == {a, b} for item in annotations)
    assert all(item["expert_level"] == 2 for item in annotations)
    assert all(item["status"] == "review_pending" for item in annotations)


def test_list_annotations_includes_all_statuses(client, scientist, seed_user, login_as):
    dive = _make_dive(client)
    a = _make_image(client, dive, "sa.png")
    b = _make_image(client, dive, "sb.png")
    _open_pair(client, a, b)

    login_as(seed_user(username="ann2", role="annotator", expert_level=0))
    u = _create_annotation(client, a, b)

    login_as(scientist)
    assert client.post(f"/api/v1/annotate/points/review/{u}/approve").status_code == 200

    resp = client.get(f"/api/v1/dataset/annotations?dive={dive}")
    assert resp.status_code == 200, resp.text
    annotations = resp.json()["annotations"]
    assert len(annotations) == 1
    assert annotations[0]["status"] == "approved"


def test_list_annotations_excludes_other_dives(client, scientist, seed_user, login_as):
    dive_a = _make_dive(client, title="dive-a")
    dive_b = _make_dive(client, title="dive-b")
    a1 = _make_image(client, dive_a, "a1.png")
    a2 = _make_image(client, dive_a, "a2.png")
    b1 = _make_image(client, dive_b, "b1.png")
    b2 = _make_image(client, dive_b, "b2.png")
    _open_pair(client, a1, a2)
    _open_pair(client, b1, b2)

    login_as(seed_user(username="ann3", role="annotator", expert_level=0))
    u_a = _create_annotation(client, a1, a2)
    _create_annotation(client, b1, b2)

    login_as(scientist)
    resp = client.get(f"/api/v1/dataset/annotations?dive={dive_a}")
    assert resp.status_code == 200
    annotations = resp.json()["annotations"]
    assert [item["uuid"] for item in annotations] == [u_a]


def test_list_annotations_empty_pair_returns_empty_list(client, scientist):
    dive = _make_dive(client)
    a = _make_image(client, dive, "ea.png")
    b = _make_image(client, dive, "eb.png")
    _open_pair(client, a, b)

    resp = client.get(f"/api/v1/dataset/annotations?dive={dive}")
    assert resp.status_code == 200
    assert resp.json() == {"annotations": []}


def test_list_annotations_unknown_dive_is_404(client, scientist):
    resp = client.get(f"/api/v1/dataset/annotations?dive={_new_uuid()}")
    assert resp.status_code == 404


def test_list_annotations_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann4", role="annotator"))
    resp = client.get(f"/api/v1/dataset/annotations?dive={_new_uuid()}")
    assert resp.status_code == 403


def test_export_annotations_csv_returns_raw_user_rows(client, scientist, seed_user, login_as):
    dive = _make_dive(client, title="dive-export")
    a = _make_image(client, dive, "ea.png")
    b = _make_image(client, dive, "eb.png")
    _open_pair(client, a, b)

    user1 = seed_user(username="ann-export-1", role="annotator", expert_level=1)
    user2 = seed_user(username="ann-export-2", role="annotator", expert_level=3)

    login_as(user1)
    _create_annotation(client, a, b, x1=10, y1=20, x2=30, y2=40)
    login_as(user2)
    _create_annotation(client, a, b, x1=11, y1=21, x2=31, y2=41)

    login_as(scientist)
    resp = client.get(f"/api/v1/dataset/annotations/export?dive={dive}")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment;" in resp.headers["content-disposition"]

    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert len(rows) == 2
    assert {row["created_by_username"] for row in rows} == {"ann-export-1", "ann-export-2"}
    assert {row["image_a_filename"] for row in rows} == {"ea.png"}
    assert {row["image_b_filename"] for row in rows} == {"eb.png"}


def test_export_annotations_csv_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann-export-blocked", role="annotator"))
    resp = client.get("/api/v1/dataset/annotations/export")
    assert resp.status_code == 403


def test_export_annotations_csv_unknown_dive_is_404(client, scientist):
    resp = client.get(f"/api/v1/dataset/annotations/export?dive={_new_uuid()}")
    assert resp.status_code == 404
