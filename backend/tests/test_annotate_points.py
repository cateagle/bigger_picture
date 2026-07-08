import base64
import io
import uuid

import pytest
from PIL import Image as PILImage
from sqlalchemy import text

from src import config


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _png_b64(width=10, height=10) -> str:
    img = PILImage.new("RGB", (width, height), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _make_dive(client, title="dive") -> str:
    region = _new_uuid()
    assert (
        client.post("/api/v1/dataset/regions/create", json={"uuid": region, "title": title + "-r"}).status_code == 201
    )
    camera = _new_uuid()
    assert (
        client.post("/api/v1/dataset/cameras/create", json={"uuid": camera, "title": title + "-c"}).status_code == 201
    )
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


def _make_label(client, scope="s", title="t") -> str:
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": u, "scope": scope, "title": title},
    )
    assert resp.status_code == 201, resp.text
    return u


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


@pytest.fixture
def dataset(client, seed_user, login_as):
    """Build a dataset as a scientist: 4 images, open image pairs, a label."""
    sci = seed_user(username="sci", role="scientist", expert_level=5)
    login_as(sci)
    dive = _make_dive(client)
    imgs = [_make_image(client, dive, f"img{i}.png") for i in range(4)]
    _open_pair(client, imgs[0], imgs[1])
    _open_pair(client, imgs[1], imgs[2])
    # imgs[2]/imgs[3] pair exists but stays hidden (not open).
    assert (
        client.post(
            "/api/v1/dataset/pairs/create",
            json={"image_a": imgs[2], "image_b": imgs[3]},
        ).status_code
        == 201
    )
    label = _make_label(client)
    return {"scientist": sci, "images": imgs, "label": label, "dive": dive}


@pytest.fixture
def annotator(client, seed_user, login_as, dataset):
    user = seed_user(username="ann", role="annotator", expert_level=1)
    login_as(user)
    return user


def _age_annotation(client, uuid_str, created_at):
    """Directly rewrite an annotation's created_at in the DB."""
    engine = client.app.state.engine
    raw = uuid.UUID(uuid_str).bytes
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE point_annotations SET created_at = :ts WHERE uuid = :u"),
            {"ts": created_at, "u": raw},
        )


def _coords(**over):
    base = {"x1": 1, "y1": 2, "x2": 3, "y2": 4}
    base.update(over)
    return base


# ------------------------- create -------------------------


def test_create_happy_no_label(client, dataset, annotator):
    imgs = dataset["images"]
    u = _new_uuid()
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": u, "image_a": imgs[0], "image_b": imgs[1], **_coords()},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["uuid"] == u
    assert body["status"] == "review_pending"
    assert body["expert_level"] == annotator.expert_level == 1
    assert body["label_id"] is None
    assert body["confidence"] is None
    assert body["x1"] == 1 and body["y1"] == 2 and body["x2"] == 3 and body["y2"] == 4
    assert body["created_by"] == str(uuid.UUID(bytes=annotator.uuid))
    assert body["reviewed_at"] is None
    assert {body["image_a"], body["image_b"]} == {imgs[0], imgs[1]}


def test_create_happy_with_label(client, dataset, annotator):
    imgs = dataset["images"]
    u = _new_uuid()
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": u, "image_a": imgs[0], "image_b": imgs[1], "label_id": dataset["label"], **_coords()},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["label_id"] == dataset["label"]


def test_create_unknown_label_is_404(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "label_id": _new_uuid(), **_coords()},
    )
    assert resp.status_code == 404, resp.text


def test_create_negative_coord_is_422(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], **_coords(x1=-1)},
    )
    assert resp.status_code == 422, resp.text


def test_create_pair_not_open_is_409(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": _new_uuid(), "image_a": imgs[2], "image_b": imgs[3], **_coords()},
    )
    assert resp.status_code == 409, resp.text


def test_create_missing_image_is_404(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": _new_uuid(), **_coords()},
    )
    assert resp.status_code == 404, resp.text


def test_create_missing_pair_is_404(client, dataset, annotator):
    imgs = dataset["images"]
    # imgs[0]/imgs[3] have no image pair at all.
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[3], **_coords()},
    )
    assert resp.status_code == 404, resp.text


def test_create_uuid_conflict_is_409(client, dataset, annotator):
    imgs = dataset["images"]
    u = _new_uuid()
    assert (
        client.post(
            "/api/v1/annotate/points/create",
            json={"uuid": u, "image_a": imgs[0], "image_b": imgs[1], **_coords()},
        ).status_code
        == 201
    )
    resp = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": u, "image_a": imgs[1], "image_b": imgs[2], **_coords()},
    )
    assert resp.status_code == 409, resp.text


# ------------------------- batch/create -------------------------


def test_batch_create_multiple(client, dataset, annotator):
    imgs = dataset["images"]
    items = [
        {"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], **_coords()},
        {"uuid": _new_uuid(), "image_a": imgs[1], "image_b": imgs[2], "label_id": dataset["label"], **_coords()},
    ]
    resp = client.post("/api/v1/annotate/points/batch/create", json=items)
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 2


def test_batch_create_uuid_conflict_rolls_back(client, dataset, annotator):
    imgs = dataset["images"]
    dup = _new_uuid()
    items = [
        {"uuid": dup, "image_a": imgs[0], "image_b": imgs[1], **_coords()},
        {"uuid": dup, "image_a": imgs[1], "image_b": imgs[2], **_coords()},
    ]
    resp = client.post("/api/v1/annotate/points/batch/create", json=items)
    assert resp.status_code == 409, resp.text
    ok = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": dup, "image_a": imgs[0], "image_b": imgs[1], **_coords()},
    )
    assert ok.status_code == 201, ok.text


def test_batch_create_bad_pair_rolls_back(client, dataset, annotator):
    imgs = dataset["images"]
    good = _new_uuid()
    items = [
        {"uuid": good, "image_a": imgs[0], "image_b": imgs[1], **_coords()},
        {"uuid": _new_uuid(), "image_a": imgs[2], "image_b": imgs[3], **_coords()},  # not open -> 409
    ]
    resp = client.post("/api/v1/annotate/points/batch/create", json=items)
    assert resp.status_code == 409, resp.text
    ok = client.post(
        "/api/v1/annotate/points/create",
        json={"uuid": good, "image_a": imgs[0], "image_b": imgs[1], **_coords()},
    )
    assert ok.status_code == 201, ok.text


# ------------------------- correction -------------------------


def _create_annotation(client, imgs, label=None, **coords):
    u = _new_uuid()
    body = {"uuid": u, "image_a": imgs[0], "image_b": imgs[1], **_coords(**coords)}
    if label is not None:
        body["label_id"] = label
    resp = client.post("/api/v1/annotate/points/create", json=body)
    assert resp.status_code == 201, resp.text
    return u


def test_correction_updates_coords(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": u, **_coords(x1=10, y1=20, x2=30, y2=40)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["x1"] == 10 and body["y1"] == 20 and body["x2"] == 30 and body["y2"] == 40


def test_correction_sets_label(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # no label
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": u, "label_id": dataset["label"], **_coords()},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["label_id"] == dataset["label"]


def test_correction_clears_label_with_explicit_null(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs, label=dataset["label"])
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": u, "label_id": None, **_coords()},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["label_id"] is None


def test_correction_missing_label_key_keeps_label(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs, label=dataset["label"])
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": u, **_coords(x1=9)},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["label_id"] == dataset["label"]


def test_correction_negative_coord_is_422(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": u, **_coords(y2=-5)},
    )
    assert resp.status_code == 422, resp.text


def test_correction_by_non_creator_is_403(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    other = seed_user(username="other", role="annotator", expert_level=1)
    login_as(other)
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": u, **_coords()},
    )
    assert resp.status_code == 403, resp.text


def test_correction_after_review_is_409(client, dataset, annotator, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    login_as(dataset["scientist"])
    assert client.post(f"/api/v1/annotate/points/review/{u}/approve").status_code == 200
    login_as(annotator)
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": u, **_coords()},
    )
    assert resp.status_code == 409, resp.text


def test_correction_window_expired_is_403(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    _age_annotation(client, u, created_at=1)
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": u, **_coords()},
    )
    assert resp.status_code == 403, resp.text
    assert "window" in resp.json()["detail"].lower()


def test_correction_window_expired_via_config(client, dataset, annotator, monkeypatch):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    monkeypatch.setattr(config, "SELF_CORRECTION_TIME_LIMIT_MS", 0)
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": u, **_coords()},
    )
    assert resp.status_code == 403, resp.text


def test_correction_missing_is_404(client, dataset, annotator):
    resp = client.post(
        "/api/v1/annotate/points/correction",
        json={"uuid": _new_uuid(), **_coords()},
    )
    assert resp.status_code == 404, resp.text


# ------------------------- review -------------------------


def test_self_review_is_403(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    resp = client.post(f"/api/v1/annotate/points/review/{u}/approve")
    assert resp.status_code == 403, resp.text


def test_low_expert_non_creator_blocked(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    low = seed_user(username="low", role="annotator", expert_level=0)
    login_as(low)
    resp = client.post(f"/api/v1/annotate/points/review/{u}/approve")
    assert resp.status_code == 403, resp.text


def test_equal_expert_non_creator_blocked(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    peer = seed_user(username="peer", role="annotator", expert_level=1)
    login_as(peer)
    resp = client.post(f"/api/v1/annotate/points/review/{u}/approve")
    assert resp.status_code == 403, resp.text


def test_higher_expert_annotator_can_approve(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    senior = seed_user(username="senior", role="annotator", expert_level=3)
    login_as(senior)
    resp = client.post(f"/api/v1/annotate/points/review/{u}/approve")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "approved"
    assert body["reviewed_by"] == str(uuid.UUID(bytes=senior.uuid))
    assert body["reviewed_at"] is not None


def test_scientist_can_fail_regardless_of_expert(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    sci = seed_user(username="sci2", role="scientist", expert_level=0)
    login_as(sci)
    resp = client.post(f"/api/v1/annotate/points/review/{u}/fail")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "review_failed"


def test_review_non_pending_is_409(client, dataset, annotator, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    login_as(dataset["scientist"])
    assert client.post(f"/api/v1/annotate/points/review/{u}/approve").status_code == 200
    resp = client.post(f"/api/v1/annotate/points/review/{u}/fail")
    assert resp.status_code == 409, resp.text


def test_review_missing_is_404(client, dataset, annotator, login_as):
    login_as(dataset["scientist"])
    resp = client.post(f"/api/v1/annotate/points/review/{_new_uuid()}/approve")
    assert resp.status_code == 404, resp.text


# ------------------------- next -------------------------


def _set_pair_fields(client, image_a, image_b, difficulty=None, priority=None, created_at=None):
    engine = client.app.state.engine
    id_a = uuid.UUID(image_a).bytes
    id_b = uuid.UUID(image_b).bytes
    with engine.begin() as conn:
        img1 = conn.execute(text("SELECT id FROM images WHERE uuid = :u"), {"u": id_a}).scalar_one()
        img2 = conn.execute(text("SELECT id FROM images WHERE uuid = :u"), {"u": id_b}).scalar_one()
        lo, hi = sorted((img1, img2))
        updates = {}
        if difficulty is not None:
            updates["difficulty"] = difficulty
        if priority is not None:
            updates["priority"] = priority
        if created_at is not None:
            updates["created_at"] = created_at
        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            conn.execute(
                text(f"UPDATE image_pairs SET {set_clause} WHERE image1_id = :lo AND image2_id = :hi"),
                {**updates, "lo": lo, "hi": hi},
            )


def test_next_default_n_returns_one(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    pair = body[0]
    assert {pair["image1"]["uuid"], pair["image2"]["uuid"]} <= set(imgs)
    assert pair["status"] == "open"


def test_next_n_two_orders_by_priority_then_age(client, dataset, annotator):
    imgs = dataset["images"]
    _set_pair_fields(client, imgs[0], imgs[1], priority=None, created_at=200)
    _set_pair_fields(client, imgs[1], imgs[2], priority=5, created_at=100)

    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}/2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2
    # priority=5 pair (imgs[1]/imgs[2]) sorts first since non-null priority beats null.
    assert {body[0]["image1"]["uuid"], body[0]["image2"]["uuid"]} == {imgs[1], imgs[2]}
    assert {body[1]["image1"]["uuid"], body[1]["image2"]["uuid"]} == {imgs[0], imgs[1]}


def test_next_excludes_pair_annotated_by_caller(client, dataset, annotator):
    imgs = dataset["images"]
    _create_annotation(client, [imgs[0], imgs[1]])

    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}/2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for pair in body:
        assert {pair["image1"]["uuid"], pair["image2"]["uuid"]} != {imgs[0], imgs[1]}


def test_next_includes_pair_annotated_by_other_user(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    _create_annotation(client, [imgs[0], imgs[1]])
    other = seed_user(username="other-next", role="annotator", expert_level=1)
    login_as(other)

    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}/2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    pairs = [{p["image1"]["uuid"], p["image2"]["uuid"]} for p in body]
    assert {imgs[0], imgs[1]} in pairs


def test_next_excludes_non_open_pair(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}/10")
    assert resp.status_code == 200, resp.text
    pairs = [{p["image1"]["uuid"], p["image2"]["uuid"]} for p in resp.json()]
    assert {imgs[2], imgs[3]} not in pairs


def test_next_excludes_pair_above_expert_level(client, dataset, annotator):
    imgs = dataset["images"]
    _set_pair_fields(client, imgs[0], imgs[1], difficulty=annotator.expert_level + 1)

    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}/10")
    assert resp.status_code == 200, resp.text
    pairs = [{p["image1"]["uuid"], p["image2"]["uuid"]} for p in resp.json()]
    assert {imgs[0], imgs[1]} not in pairs


def test_next_includes_pair_at_or_below_expert_level(client, dataset, annotator):
    imgs = dataset["images"]
    _set_pair_fields(client, imgs[0], imgs[1], difficulty=annotator.expert_level)

    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}/10")
    assert resp.status_code == 200, resp.text
    pairs = [{p["image1"]["uuid"], p["image2"]["uuid"]} for p in resp.json()]
    assert {imgs[0], imgs[1]} in pairs


def test_next_excludes_pair_from_other_dive(client, dataset, annotator, login_as):
    login_as(dataset["scientist"])
    other_dive = _make_dive(client, title="other-dive")
    other_imgs = [_make_image(client, other_dive, f"other-img{i}.png") for i in range(2)]
    _open_pair(client, other_imgs[0], other_imgs[1])
    login_as(annotator)

    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}/10")
    assert resp.status_code == 200, resp.text
    pairs = [{p["image1"]["uuid"], p["image2"]["uuid"]} for p in resp.json()]
    assert {other_imgs[0], other_imgs[1]} not in pairs


def test_next_unknown_dive_is_404(client, dataset, annotator):
    resp = client.get(f"/api/v1/annotate/points/next/{_new_uuid()}")
    assert resp.status_code == 404, resp.text


def test_next_n_zero_is_422(client, dataset, annotator):
    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}/0")
    assert resp.status_code == 422, resp.text


def test_next_no_matches_is_empty_list(client, dataset, annotator):
    imgs = dataset["images"]
    _create_annotation(client, [imgs[0], imgs[1]])
    _create_annotation(client, [imgs[1], imgs[2]])

    resp = client.get(f"/api/v1/annotate/points/next/{dataset['dive']}/10")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []
