import base64
import io
import uuid

import pytest
from PIL import Image as PILImage
from sqlalchemy import text

from src import config
from src.constants import (
    ANNOTATION_APPROVED,
    ANNOTATION_REVIEW_FAILED,
    ANNOTATION_REVIEW_PENDING,
    CANDIDATE_STATUS_INT,
    PAIR_STATUS_INT,
    CandidateStatus,
    PairStatus,
)


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
    return {"scientist": sci, "images": imgs, "dive": dive}


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


def test_create_second_vote_by_same_user_for_same_candidate_is_409(client, dataset, annotator):
    imgs = dataset["images"]
    assert (
        client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "no_overlap": True},
        ).status_code
        == 201
    )
    resp = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "no_overlap": False},
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


def test_pure_weighted_consensus_overrides_raw_minority_and_promotes_candidate(
    client, dataset, annotator, seed_user, login_as
):
    """2 novices vote no_overlap (weight 1 each = 2), then 4 experts vote
    overlap (weight 2 each = 8): total weight 10 hits
    CANDIDATE_CONSENSUS_MIN_WEIGHT with an overlap share of 0.8, closing the
    candidate via the weighted path - while the raw count is 6 with only a
    4/6 = 0.667 overlap share, which would NOT independently satisfy
    CANDIDATE_AGREEMENT_THRESHOLD (0.7). This proves expert weighting, not
    raw majority, drives the outcome.
    """
    imgs = dataset["images"]

    novices = [
        seed_user(username="novice1", role="annotator", expert_level=0),
        seed_user(username="novice2", role="annotator", expert_level=0),
    ]
    experts = [
        seed_user(username="expert1", role="annotator", expert_level=3),
        seed_user(username="expert2", role="annotator", expert_level=3),
        seed_user(username="expert3", role="annotator", expert_level=3),
        seed_user(username="expert4", role="annotator", expert_level=3),
    ]

    for voter in novices:
        login_as(voter)
        resp = client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "no_overlap": True},
        )
        assert resp.status_code == 201, resp.text

    for voter in experts:
        login_as(voter)
        resp = client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "no_overlap": False},
        )
        assert resp.status_code == 201, resp.text

    engine = client.app.state.engine
    with engine.begin() as conn:
        candidate_status = conn.execute(
            text(
                "SELECT cp.status_id FROM candidate_pairs cp "
                "JOIN images i1 ON i1.id = cp.image1_id "
                "JOIN images i2 ON i2.id = cp.image2_id "
                "WHERE i1.uuid = :a AND i2.uuid = :b"
            ),
            {"a": uuid.UUID(imgs[0]).bytes, "b": uuid.UUID(imgs[1]).bytes},
        ).scalar_one()

    assert candidate_status == CANDIDATE_STATUS_INT[CandidateStatus.HAS_OVERLAP]


def test_weighted_no_overlap_consensus_closes_candidate_without_pair(client, dataset, annotator, seed_user, login_as):
    """Both the weighted (5 experts x weight 2 = 10) and raw (5/5 = 1.0)
    thresholds agree here, so this doesn't isolate one path - it exists to
    prove no_overlap consensus never creates an ImagePair.
    """
    imgs = dataset["images"]

    voters = [
        seed_user(username="no1", role="annotator", expert_level=3),
        seed_user(username="no2", role="annotator", expert_level=3),
        seed_user(username="no3", role="annotator", expert_level=3),
        seed_user(username="no4", role="annotator", expert_level=3),
        seed_user(username="no5", role="annotator", expert_level=3),
    ]

    for voter in voters:
        login_as(voter)
        resp = client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": _new_uuid(), "image_a": imgs[1], "image_b": imgs[2], "no_overlap": True},
        )
        assert resp.status_code == 201, resp.text

    engine = client.app.state.engine
    with engine.begin() as conn:
        candidate_status = conn.execute(
            text(
                "SELECT cp.status_id FROM candidate_pairs cp "
                "JOIN images i1 ON i1.id = cp.image1_id "
                "JOIN images i2 ON i2.id = cp.image2_id "
                "WHERE i1.uuid = :a AND i2.uuid = :b"
            ),
            {"a": uuid.UUID(imgs[1]).bytes, "b": uuid.UUID(imgs[2]).bytes},
        ).scalar_one()
        pair_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM image_pairs ip "
                "JOIN images i1 ON i1.id = ip.image1_id "
                "JOIN images i2 ON i2.id = ip.image2_id "
                "WHERE i1.uuid = :a AND i2.uuid = :b"
            ),
            {"a": uuid.UUID(imgs[1]).bytes, "b": uuid.UUID(imgs[2]).bytes},
        ).scalar_one()

    assert candidate_status == CANDIDATE_STATUS_INT[CandidateStatus.NO_OVERLAP]
    assert pair_count == 0


# --------------------- raw count/agreement auto-review ---------------------


def _annotation_row(client, annotation_uuid):
    engine = client.app.state.engine
    with engine.begin() as conn:
        return conn.execute(
            text("SELECT status_id, reviewed_by, reviewed_at FROM candidate_annotations WHERE uuid = :u"),
            {"u": uuid.UUID(annotation_uuid).bytes},
        ).mappings().one()


def test_raw_agreement_consensus_flips_annotations_and_grants_exp_to_winners_only(
    client, dataset, annotator, seed_user, login_as
):
    """5 low-expert votes (weight well under CANDIDATE_CONSENSUS_MIN_WEIGHT,
    so only the raw count/agreement path can fire): 4 overlap, 1 no_overlap.
    Raw share = 4/5 = 0.8 >= CANDIDATE_AGREEMENT_THRESHOLD (0.7) at count 5
    == CANDIDATE_MIN_ANNOTATIONS. Winners (overlap voters) get approved +
    exp; the loser (no_overlap voter) gets review_failed + no exp; the
    candidate becomes has_overlap.
    """
    imgs = dataset["images"]
    voters = [seed_user(username=f"raw{i}", role="annotator", expert_level=0) for i in range(5)]
    votes = [False, False, False, False, True]  # no_overlap: 4x overlap, 1x no_overlap

    uuids = []
    exp_before = {}
    for voter, no_overlap in zip(voters, votes):
        login_as(voter)
        exp_before[voter.uuid] = _get_exp(client, voter.uuid)
        u = _new_uuid()
        resp = client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": u, "image_a": imgs[0], "image_b": imgs[1], "no_overlap": no_overlap},
        )
        assert resp.status_code == 201, resp.text
        uuids.append(u)

    engine = client.app.state.engine
    with engine.begin() as conn:
        candidate_status = conn.execute(
            text(
                "SELECT cp.status_id FROM candidate_pairs cp "
                "JOIN images i1 ON i1.id = cp.image1_id JOIN images i2 ON i2.id = cp.image2_id "
                "WHERE i1.uuid = :a AND i2.uuid = :b"
            ),
            {"a": uuid.UUID(imgs[0]).bytes, "b": uuid.UUID(imgs[1]).bytes},
        ).scalar_one()
    assert candidate_status == CANDIDATE_STATUS_INT[CandidateStatus.HAS_OVERLAP]

    for voter, no_overlap, ann_uuid in zip(voters, votes, uuids):
        row = _annotation_row(client, ann_uuid)
        assert row["reviewed_by"] is None
        assert row["reviewed_at"] is not None
        if no_overlap:
            assert row["status_id"] == ANNOTATION_REVIEW_FAILED
            assert _get_exp(client, voter.uuid) == exp_before[voter.uuid]
        else:
            assert row["status_id"] == ANNOTATION_APPROVED
            assert _get_exp(client, voter.uuid) == exp_before[voter.uuid] + config.CANDIDATE_ANNOTATION_REVIEW_EXP


def test_auto_review_exp_not_granted_before_threshold_met(client, dataset, annotator, seed_user, login_as):
    """After only 4 of the 5 required votes, nothing has fired yet: no exp
    granted, annotations still review_pending, candidate still open.
    """
    imgs = dataset["images"]
    voters = [seed_user(username=f"partial{i}", role="annotator", expert_level=0) for i in range(4)]
    uuids = []
    exp_before = {}
    for voter in voters:
        login_as(voter)
        exp_before[voter.uuid] = _get_exp(client, voter.uuid)
        u = _new_uuid()
        resp = client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": u, "image_a": imgs[0], "image_b": imgs[1], "no_overlap": False},
        )
        assert resp.status_code == 201, resp.text
        uuids.append(u)

    for voter in voters:
        assert _get_exp(client, voter.uuid) == exp_before[voter.uuid]
    for ann_uuid in uuids:
        row = _annotation_row(client, ann_uuid)
        assert row["status_id"] == ANNOTATION_REVIEW_PENDING
        assert row["reviewed_at"] is None


def test_auto_review_creates_image_pair_on_has_overlap(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    voters = [seed_user(username=f"ip{i}", role="annotator", expert_level=0) for i in range(5)]
    for voter in voters:
        login_as(voter)
        resp = client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "no_overlap": False},
        )
        assert resp.status_code == 201, resp.text

    engine = client.app.state.engine
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT ip.status_id FROM image_pairs ip "
                "JOIN images i1 ON i1.id = ip.image1_id JOIN images i2 ON i2.id = ip.image2_id "
                "WHERE i1.uuid = :a AND i2.uuid = :b"
            ),
            {"a": uuid.UUID(imgs[0]).bytes, "b": uuid.UUID(imgs[1]).bytes},
        ).mappings().one()
    assert row["status_id"] == PAIR_STATUS_INT[PairStatus.HIDDEN]


def test_auto_review_no_double_image_pair_if_one_preexists(client, dataset, annotator, seed_user, login_as):
    """If an ImagePair for this image combo somehow already exists (e.g. a
    scientist pre-created one), auto-review must not error or duplicate it.
    """
    imgs = dataset["images"]
    login_as(dataset["scientist"])
    resp = client.post(
        "/api/v1/dataset/pairs/create",
        json={"image_a": imgs[0], "image_b": imgs[1]},
    )
    assert resp.status_code == 201, resp.text

    voters = [seed_user(username=f"dup{i}", role="annotator", expert_level=0) for i in range(5)]
    for voter in voters:
        login_as(voter)
        resp = client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "no_overlap": False},
        )
        assert resp.status_code == 201, resp.text

    engine = client.app.state.engine
    with engine.begin() as conn:
        count = conn.execute(
            text(
                "SELECT COUNT(*) FROM image_pairs ip "
                "JOIN images i1 ON i1.id = ip.image1_id JOIN images i2 ON i2.id = ip.image2_id "
                "WHERE i1.uuid = :a AND i2.uuid = :b"
            ),
            {"a": uuid.UUID(imgs[0]).bytes, "b": uuid.UUID(imgs[1]).bytes},
        ).scalar_one()
    assert count == 1


def test_auto_review_closes_pair_and_further_votes_409_without_double_exp(
    client, dataset, annotator, seed_user, login_as
):
    imgs = dataset["images"]
    voters = [seed_user(username=f"idem{i}", role="annotator", expert_level=0) for i in range(5)]
    for voter in voters:
        login_as(voter)
        resp = client.post(
            "/api/v1/annotate/candidate/create",
            json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "no_overlap": False},
        )
        assert resp.status_code == 201, resp.text

    exp_after_close = {voter.uuid: _get_exp(client, voter.uuid) for voter in voters}

    extra = seed_user(username="latecomer", role="annotator", expert_level=0)
    login_as(extra)
    resp = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": _new_uuid(), "image_a": imgs[0], "image_b": imgs[1], "no_overlap": False},
    )
    assert resp.status_code == 409, resp.text

    for voter in voters:
        assert _get_exp(client, voter.uuid) == exp_after_close[voter.uuid]


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


# ------------------------- review exp -------------------------


def _get_exp(client, user_uuid: bytes) -> int:
    engine = client.app.state.engine
    with engine.begin() as conn:
        return conn.execute(text("SELECT exp FROM users WHERE uuid = :u"), {"u": user_uuid}).scalar_one()


def test_review_approve_grants_exp_to_reviewer_and_creator(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator: annotator
    senior = seed_user(username="senior-exp", role="annotator", expert_level=3)
    login_as(senior)
    senior_before = _get_exp(client, senior.uuid)
    creator_before = _get_exp(client, annotator.uuid)
    resp = client.post(f"/api/v1/annotate/candidate/review/{u}/approve")
    assert resp.status_code == 200, resp.text
    assert _get_exp(client, senior.uuid) == senior_before + config.CANDIDATE_ANNOTATION_REVIEW_EXP
    assert _get_exp(client, annotator.uuid) == creator_before + config.CANDIDATE_ANNOTATION_REVIEW_EXP


def test_review_fail_grants_exp_to_reviewer_only(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator: annotator
    senior = seed_user(username="senior-exp2", role="annotator", expert_level=3)
    login_as(senior)
    senior_before = _get_exp(client, senior.uuid)
    creator_before = _get_exp(client, annotator.uuid)
    resp = client.post(f"/api/v1/annotate/candidate/review/{u}/fail")
    assert resp.status_code == 200, resp.text
    assert _get_exp(client, senior.uuid) == senior_before + config.CANDIDATE_ANNOTATION_REVIEW_EXP
    assert _get_exp(client, annotator.uuid) == creator_before


# ------------------------- next -------------------------


def _set_candidate_created_at(client, image_a, image_b, created_at):
    engine = client.app.state.engine
    id_a = uuid.UUID(image_a).bytes
    id_b = uuid.UUID(image_b).bytes
    with engine.begin() as conn:
        img1 = conn.execute(text("SELECT id FROM images WHERE uuid = :u"), {"u": id_a}).scalar_one()
        img2 = conn.execute(text("SELECT id FROM images WHERE uuid = :u"), {"u": id_b}).scalar_one()
        lo, hi = sorted((img1, img2))
        conn.execute(
            text("UPDATE candidate_pairs SET created_at = :ts WHERE image1_id = :lo AND image2_id = :hi"),
            {"ts": created_at, "lo": lo, "hi": hi},
        )


def test_next_default_n_returns_one(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    candidate = body[0]
    assert {candidate["image1"]["uuid"], candidate["image2"]["uuid"]} <= set(imgs)
    assert candidate["status"] == "open"


def test_next_n_two_returns_both_regardless_of_age(client, dataset, annotator):
    imgs = dataset["images"]
    _set_candidate_created_at(client, imgs[0], imgs[1], 200)
    _set_candidate_created_at(client, imgs[1], imgs[2], 100)

    resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}/2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2
    returned = {frozenset({c["image1"]["uuid"], c["image2"]["uuid"]}) for c in body}
    assert returned == {frozenset({imgs[0], imgs[1]}), frozenset({imgs[1], imgs[2]})}


def test_next_pool_size_limits_by_age(client, dataset, annotator, monkeypatch):
    imgs = dataset["images"]
    _set_candidate_created_at(client, imgs[0], imgs[1], 200)
    _set_candidate_created_at(client, imgs[1], imgs[2], 100)
    monkeypatch.setattr(config, "NEXT_ITEM_POOL_SIZE", 1)

    resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}/1")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    # With pool_size=1, only the older candidate (created_at=100) can ever be sampled.
    assert {body[0]["image1"]["uuid"], body[0]["image2"]["uuid"]} == {imgs[1], imgs[2]}


def test_next_n_returns_random_order_across_requests(client, dataset, annotator):
    imgs = dataset["images"]
    _set_candidate_created_at(client, imgs[0], imgs[1], 200)
    _set_candidate_created_at(client, imgs[1], imgs[2], 100)

    first_seen = set()
    for _ in range(30):
        resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}/2")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        first_seen.add(frozenset({body[0]["image1"]["uuid"], body[0]["image2"]["uuid"]}))
    assert first_seen == {frozenset({imgs[0], imgs[1]}), frozenset({imgs[1], imgs[2]})}


def test_next_excludes_candidate_annotated_by_caller(client, dataset, annotator):
    imgs = dataset["images"]
    _create_annotation(client, [imgs[0], imgs[1]])

    resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}/2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for candidate in body:
        assert {candidate["image1"]["uuid"], candidate["image2"]["uuid"]} != {imgs[0], imgs[1]}


def test_next_includes_candidate_annotated_by_other_user(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    _create_annotation(client, [imgs[0], imgs[1]])
    other = seed_user(username="other-next", role="annotator", expert_level=1)
    login_as(other)

    resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}/2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    candidates = [{c["image1"]["uuid"], c["image2"]["uuid"]} for c in body]
    assert {imgs[0], imgs[1]} in candidates


def test_next_excludes_non_open_candidate(client, dataset, annotator):
    imgs = dataset["images"]
    resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}/10")
    assert resp.status_code == 200, resp.text
    candidates = [{c["image1"]["uuid"], c["image2"]["uuid"]} for c in resp.json()]
    assert {imgs[2], imgs[3]} not in candidates


def test_next_excludes_candidate_from_other_dive(client, dataset, annotator, login_as):
    login_as(dataset["scientist"])
    other_dive = _make_dive(client, title="other-dive")
    other_imgs = [_make_image(client, other_dive, f"other-img{i}.png") for i in range(2)]
    _open_candidate(client, other_imgs[0], other_imgs[1])
    login_as(annotator)

    resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}/10")
    assert resp.status_code == 200, resp.text
    candidates = [{c["image1"]["uuid"], c["image2"]["uuid"]} for c in resp.json()]
    assert {other_imgs[0], other_imgs[1]} not in candidates


def test_next_unknown_dive_is_404(client, dataset, annotator):
    resp = client.get(f"/api/v1/annotate/candidate/next/{_new_uuid()}")
    assert resp.status_code == 404, resp.text


def test_next_n_zero_is_422(client, dataset, annotator):
    resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}/0")
    assert resp.status_code == 422, resp.text


def test_next_no_matches_is_empty_list(client, dataset, annotator):
    imgs = dataset["images"]
    _create_annotation(client, [imgs[0], imgs[1]])
    _create_annotation(client, [imgs[1], imgs[2]])

    resp = client.get(f"/api/v1/annotate/candidate/next/{dataset['dive']}/10")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


# ------------------------- review next -------------------------


def test_review_next_default_n_returns_one(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    senior = seed_user(username="senior-rn", role="annotator", expert_level=3)
    login_as(senior)

    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["uuid"] == u
    assert body[0]["status"] == "review_pending"


def test_review_next_n_two_returns_both_regardless_of_age(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u1 = _create_annotation(client, imgs)
    u2 = _create_annotation(client, [imgs[1], imgs[2]])
    _age_annotation(client, u1, created_at=200)
    _age_annotation(client, u2, created_at=100)

    senior = seed_user(username="senior-rn2", role="annotator", expert_level=3)
    login_as(senior)

    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}/2")
    assert resp.status_code == 200, resp.text
    assert {a["uuid"] for a in resp.json()} == {u1, u2}


def test_review_next_pool_size_limits_by_age(client, dataset, annotator, seed_user, login_as, monkeypatch):
    imgs = dataset["images"]
    u1 = _create_annotation(client, imgs)
    u2 = _create_annotation(client, [imgs[1], imgs[2]])
    _age_annotation(client, u1, created_at=200)
    _age_annotation(client, u2, created_at=100)
    monkeypatch.setattr(config, "NEXT_ITEM_POOL_SIZE", 1)

    senior = seed_user(username="senior-rn3", role="annotator", expert_level=3)
    login_as(senior)

    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}/1")
    assert resp.status_code == 200, resp.text
    # With pool_size=1, only the older annotation (u2, created_at=100) can ever be sampled.
    assert [a["uuid"] for a in resp.json()] == [u2]


def test_review_next_n_returns_random_order_across_requests(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u1 = _create_annotation(client, imgs)
    u2 = _create_annotation(client, [imgs[1], imgs[2]])
    _age_annotation(client, u1, created_at=200)
    _age_annotation(client, u2, created_at=100)

    senior = seed_user(username="senior-rn4", role="annotator", expert_level=3)
    login_as(senior)

    first_seen = set()
    for _ in range(30):
        resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}/2")
        assert resp.status_code == 200, resp.text
        first_seen.add(resp.json()[0]["uuid"])
    assert first_seen == {u1, u2}


def test_review_next_excludes_annotation_created_by_caller(client, dataset, annotator):
    imgs = dataset["images"]
    _create_annotation(client, imgs)

    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_review_next_includes_annotation_created_by_other_user(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    senior = seed_user(username="senior-rn3", role="annotator", expert_level=3)
    login_as(senior)

    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    assert [a["uuid"] for a in resp.json()] == [u]


def test_review_next_excludes_non_pending_annotation(client, dataset, annotator, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)
    login_as(dataset["scientist"])
    assert client.post(f"/api/v1/annotate/candidate/review/{u}/approve").status_code == 200

    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_review_next_excludes_annotation_from_other_dive(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    local_u = _create_annotation(client, imgs)

    login_as(dataset["scientist"])
    other_dive = _make_dive(client, title="other-dive")
    other_imgs = [_make_image(client, other_dive, f"other-img{i}.png") for i in range(2)]
    _open_candidate(client, other_imgs[0], other_imgs[1])
    other_annotator = seed_user(username="other-ann-rn", role="annotator", expert_level=1)
    login_as(other_annotator)
    _create_annotation(client, other_imgs)

    senior = seed_user(username="senior-rn4", role="annotator", expert_level=3)
    login_as(senior)
    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    assert [a["uuid"] for a in resp.json()] == [local_u]


def test_review_next_unknown_dive_is_404(client, dataset, annotator):
    resp = client.get(f"/api/v1/annotate/candidate/review/next/{_new_uuid()}")
    assert resp.status_code == 404, resp.text


def test_review_next_n_zero_is_422(client, dataset, annotator):
    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}/0")
    assert resp.status_code == 422, resp.text


def test_review_next_no_matches_is_empty_list(client, dataset, annotator, seed_user, login_as):
    senior = seed_user(username="senior-rn5", role="annotator", expert_level=3)
    login_as(senior)
    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_review_next_low_expert_non_creator_gets_empty_list(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    _create_annotation(client, imgs)  # creator expert_level 1
    low = seed_user(username="low-rn", role="annotator", expert_level=0)
    login_as(low)
    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_review_next_equal_expert_non_creator_gets_empty_list(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    _create_annotation(client, imgs)  # creator expert_level 1
    peer = seed_user(username="peer-rn", role="annotator", expert_level=1)
    login_as(peer)
    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_review_next_higher_expert_non_creator_sees_it(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    senior = seed_user(username="senior-rn6", role="annotator", expert_level=3)
    login_as(senior)
    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    assert [a["uuid"] for a in resp.json()] == [u]


def test_review_next_scientist_sees_it_regardless_of_expert(client, dataset, annotator, seed_user, login_as):
    imgs = dataset["images"]
    u = _create_annotation(client, imgs)  # creator expert_level 1
    sci = seed_user(username="sci-rn", role="scientist", expert_level=0)
    login_as(sci)
    resp = client.get(f"/api/v1/annotate/candidate/review/next/{dataset['dive']}")
    assert resp.status_code == 200, resp.text
    assert [a["uuid"] for a in resp.json()] == [u]
