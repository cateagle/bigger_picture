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


def _open_candidate(client, image_a, image_b):
    assert (
        client.post(
            "/api/v1/dataset/candidates/create",
            json={"image_a": image_a, "image_b": image_b},
        ).status_code
        == 201
    )
    resp = client.post(
        "/api/v1/dataset/candidates/batch/status-change/open",
        json=[{"image_a": image_a, "image_b": image_b}],
    )
    assert resp.status_code == 200, resp.text


@pytest.fixture
def dataset(client, seed_user, login_as):
    """Build a dataset as a scientist: 4 images and 3 open candidate pairs."""
    sci = seed_user(username="sci", role="scientist", expert_level=5)
    login_as(sci)
    dive = _make_dive(client)
    imgs = [_make_image(client, dive, f"img{i}.png") for i in range(4)]
    _open_candidate(client, imgs[0], imgs[1])
    _open_candidate(client, imgs[1], imgs[2])
    # imgs[2]/imgs[3] candidate exists but stays hidden (not open).
    assert (
        client.post(
            "/api/v1/dataset/candidates/create",
            json={"image_a": imgs[2], "image_b": imgs[3]},
        ).status_code
        == 201
    )
    return {"scientist": sci, "images": imgs}


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
            text("UPDATE candidate_annotations SET created_at = :ts WHERE uuid = :u"),
            {"ts": created_at, "u": raw},
        )


# ------------------------- create -------------------------


def test_create_happy(client, dataset, annotator):
    imgs = dataset["images"]
    u = _new_uuid()
    resp = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": u, "image_a": imgs[0], "image_b": imgs[1], "no_overlap": True},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["uuid"] == u
    assert body["status"] == "review_pending"
    assert body["expert_level"] == annotator.expert_level == 1
    assert body["no_overlap"] is True
    assert body["created_by"] == str(uuid.UUID(bytes=annotator.uuid))
    assert body["reviewed_at"] is None
    assert {body["image_a"], body["image_b"]} == {imgs[0], imgs[1]}


def test_create_candidate_not_open_is_409(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": _new_uuid(), "image_a": imgs[2], "image_b": imgs[3], "no_overlap": False},
    )
    assert resp.status_code == 409, resp.text


def test_create_missing_image_is_404(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": _new_uuid(), "no_overlap": False},
    )
    assert resp.status_code == 404, resp.text


def test_create_missing_candidate_is_404(client, dataset, annotator):
    imgs = dataset["images"]
    # imgs[0]/imgs[3] have no candidate pair at all.
    resp = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[3], "no_overlap": False},
    )
    assert resp.status_code == 404, resp.text


def test_create_uuid_conflict_is_409(client, dataset, annotator):
    imgs = dataset["images"]
    u = _new_uuid()
    assert (
        client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": u, "image_a": imgs[0], "image_b": imgs[1], "no_overlap": True},
        ).status_code
        == 201
    )
    resp = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": u, "image_a": imgs[1], "image_b": imgs[2], "no_overlap": True},
    )
    assert resp.status_code == 409, resp.text


# ------------------------- batch/create -------------------------


def test_batch_create_multiple(client, dataset, annotator):
    imgs = dataset["images"]
    items = [
        {"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "no_overlap": True},
        {"uuid": _new_uuid(), "image_a": imgs[1], "image_b": imgs[2], "no_overlap": False},
    ]
    resp = client.post("/api/v1/annotate/candidate/batch/create", json=items)
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 2


def test_batch_create_uuid_conflict_rolls_back(client, dataset, annotator):
    imgs = dataset["images"]
    dup = _new_uuid()
    items = [
        {"uuid": dup, "image_a": imgs[0], "image_b": imgs[1], "no_overlap": True},
        {"uuid": dup, "image_a": imgs[1], "image_b": imgs[2], "no_overlap": False},
    ]
    resp = client.post("/api/v1/annotate/candidate/batch/create", json=items)
    assert resp.status_code == 409, resp.text
    # Nothing created: the uuid can now be used successfully for a single create.
    ok = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": dup, "image_a": imgs[0], "image_b": imgs[1], "no_overlap": True},
    )
    assert ok.status_code == 201, ok.text


def test_batch_create_bad_candidate_rolls_back(client, dataset, annotator):
    imgs = dataset["images"]
    good = _new_uuid()
    items = [
        {"uuid": good, "image_a": imgs[0], "image_b": imgs[1], "no_overlap": True},
        {"uuid": _new_uuid(), "image_a": imgs[2], "image_b": imgs[3], "no_overlap": False},  # not open -> 409
    ]
    resp = client.post("/api/v1/annotate/candidate/batch/create", json=items)
    assert resp.status_code == 409, resp.text
    # good uuid still free -> nothing committed.
    ok = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": good, "image_a": imgs[0], "image_b": imgs[1], "no_overlap": True},
    )
    assert ok.status_code == 201, ok.text


# ------------------------- correction -------------------------


def _create_annotation(client, imgs, no_overlap=True):
    u = _new_uuid()
    resp = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": u, "image_a": imgs[0], "image_b": imgs[1], "no_overlap": no_overlap},
    )
    assert resp.status_code == 201, resp.text
    return u


def test_correction_by_creator_in_window(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs, no_overlap=True)
    resp = client.post(
        "/api/v1/annotate/candidate/correction",
        json={"uuid": u, "no_overlap": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["no_overlap"] is False


def test_correction_by_non_creator_is_403(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    other = seed_user(username="other", role="annotator", expert_level=1)
    login_as(other)
    resp = client.post(
        "/api/v1/annotate/candidate/correction",
        json={"uuid": u, "no_overlap": False},
    )
    assert resp.status_code == 403, resp.text


def test_correction_after_review_is_409(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    # Scientist approves it.
    login_as(dataset["scientist"])
    assert client.post(f"/api/v1/annotate/candidate/review/{u}/approve").status_code == 200
    # Creator now tries to correct -> not pending -> 409.
    login_as(annotator)
    resp = client.post(
        "/api/v1/annotate/candidate/correction",
        json={"uuid": u, "no_overlap": False},
    )
    assert resp.status_code == 409, resp.text


def test_correction_window_expired_is_403(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    # Age the row far past the correction window.
    _age_annotation(client, u, created_at=1)
    resp = client.post(
        "/api/v1/annotate/candidate/correction",
        json={"uuid": u, "no_overlap": False},
    )
    assert resp.status_code == 403, resp.text
    assert "window" in resp.json()["detail"].lower()


def test_correction_window_expired_via_config(client, dataset, annotator, monkeypatch):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    monkeypatch.setattr(config, "SELF_CORRECTION_TIME_LIMIT_MS", 0)
    resp = client.post(
        "/api/v1/annotate/candidate/correction",
        json={"uuid": u, "no_overlap": False},
    )
    assert resp.status_code == 403, resp.text


def test_correction_missing_is_404(client, dataset, annotator):
    resp = client.post(
        "/api/v1/annotate/candidate/correction",
        json={"uuid": _new_uuid(), "no_overlap": False},
    )
    assert resp.status_code == 404, resp.text


# ------------------------- review -------------------------


def test_self_review_is_403(client, dataset, annotator):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    resp = client.post(f"/api/v1/annotate/candidate/review/{u}/approve")
    assert resp.status_code == 403, resp.text


def test_low_expert_non_creator_blocked(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    # Reviewer with expert_level 0 < MIN_REVIEW_EXPERT_LEVEL(1) -> blocked.
    low = seed_user(username="low", role="annotator", expert_level=0)
    login_as(low)
    resp = client.post(f"/api/v1/annotate/candidate/review/{u}/approve")
    assert resp.status_code == 403, resp.text


def test_equal_expert_non_creator_blocked(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    # Reviewer expert_level 1 is not > creator's 1 -> blocked.
    peer = seed_user(username="peer", role="annotator", expert_level=1)
    login_as(peer)
    resp = client.post(f"/api/v1/annotate/candidate/review/{u}/approve")
    assert resp.status_code == 403, resp.text


def test_higher_expert_annotator_can_approve(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    senior = seed_user(username="senior", role="annotator", expert_level=3)
    login_as(senior)
    resp = client.post(f"/api/v1/annotate/candidate/review/{u}/approve")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "approved"
    assert body["reviewed_by"] == str(uuid.UUID(bytes=senior.uuid))
    assert body["reviewed_at"] is not None


def test_scientist_can_fail_regardless_of_expert(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    # Scientist with expert_level 0 still passes by role.
    sci = seed_user(username="sci2", role="scientist", expert_level=0)
    login_as(sci)
    resp = client.post(f"/api/v1/annotate/candidate/review/{u}/fail")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "review_failed"


def test_review_non_pending_is_409(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    login_as(dataset["scientist"])
    assert client.post(f"/api/v1/annotate/candidate/review/{u}/approve").status_code == 200
    # Second review attempt -> not pending -> 409.
    resp = client.post(f"/api/v1/annotate/candidate/review/{u}/fail")
    assert resp.status_code == 409, resp.text


def test_review_missing_is_404(client, dataset, annotator, login_as):
    login_as(dataset["scientist"])
    resp = client.post(f"/api/v1/annotate/candidate/review/{_new_uuid()}/approve")
    assert resp.status_code == 404, resp.text
