import uuid

import pytest
from sqlalchemy import text

from src.services.quests import CATALOG, day_window, select_daily_quests


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _make_dive(client, title="dive") -> str:
    region = _new_uuid()
    assert client.post("/api/v1/dataset/regions/create", json={"uuid": region, "title": title + "-r"}).status_code == 201
    camera = _new_uuid()
    assert client.post("/api/v1/dataset/cameras/create", json={"uuid": camera, "title": title + "-c"}).status_code == 201
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": u, "title": title, "region": region, "camera": camera},
    )
    assert resp.status_code == 201, resp.text
    return u


def _make_image(client, dive, filepath) -> str:
    import base64
    import io

    from PIL import Image as PILImage

    img = PILImage.new("RGB", (10, 10), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/images/create",
        json={"uuid": u, "filename": filepath, "filepath": filepath, "dive_uuid": dive, "image": b64},
    )
    assert resp.status_code == 201, resp.text
    return u


def _open_candidate(client, image_a, image_b):
    assert client.post("/api/v1/dataset/candidates/create", json={"image_a": image_a, "image_b": image_b}).status_code == 201
    resp = client.post(
        "/api/v1/dataset/candidates/batch/status-change/open",
        json=[{"image_a": image_a, "image_b": image_b}],
    )
    assert resp.status_code == 200, resp.text


def _vote(client, image_a, image_b, no_overlap) -> str:
    u = _new_uuid()
    resp = client.post(
        "/api/v1/annotate/candidate/create",
        json={"uuid": u, "image_a": image_a, "image_b": image_b, "no_overlap": no_overlap},
    )
    assert resp.status_code == 201, resp.text
    return u


def _review_candidate(client, u, decision):
    assert client.post(f"/api/v1/annotate/candidate/review/{u}/{decision}").status_code == 200


def _set_reviewed_at(client, uuid_str, reviewed_at):
    engine = client.app.state.engine
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE candidate_annotations SET reviewed_at = :ts WHERE uuid = :u"),
            {"ts": reviewed_at, "u": uuid.UUID(uuid_str).bytes},
        )


@pytest.fixture
def dataset(client, seed_user, login_as):
    """Scientist-built dataset: a chain of 6 images with 5 open candidate pairs."""
    sci = seed_user(username="sci", role="scientist", expert_level=5)
    login_as(sci)
    dive = _make_dive(client)
    imgs = [_make_image(client, dive, f"img{i}.png") for i in range(6)]
    for a, b in zip(imgs, imgs[1:]):
        _open_candidate(client, a, b)
    return {"scientist": sci, "images": imgs, "dive": dive}


@pytest.fixture
def ann(client, seed_user, login_as, dataset):
    user = seed_user(username="ann", role="annotator", expert_level=1)
    login_as(user)
    return user


# The "overlaps_confirmed_5" template has the smallest target (5) that's cheap
# to reach in tests: 5 votes, all judged as overlapping, all approved.
OVERLAPS_QUEST_KEY = "overlaps_confirmed_5"


def _complete_overlaps_quest(client, dataset, ann, login_as):
    imgs = dataset["images"]
    votes = [_vote(client, a, b, no_overlap=False) for a, b in zip(imgs, imgs[1:])]
    login_as(dataset["scientist"])
    for v in votes:
        _review_candidate(client, v, "approve")
    login_as(ann)
    return votes


# ------------------------- day window -------------------------


def test_day_window_is_local_midnight_and_deterministic():
    # 2026-07-09 10:00:00 UTC.
    now_ms = 1783483200000
    start_a, end_a = day_window(now_ms)
    start_b, end_b = day_window(now_ms)
    assert (start_a, end_a) == (start_b, end_b)
    assert start_a < now_ms < end_a
    assert end_a - start_a in (23 * 3600 * 1000, 24 * 3600 * 1000, 25 * 3600 * 1000)  # DST-safe


# ------------------------- daily selection -------------------------


def test_daily_quest_set_is_seeded_only_by_day():
    start, _ = day_window(1783483200000)
    assert select_daily_quests(start) == select_daily_quests(start)


def test_daily_quest_set_is_identical_for_every_user(client, dataset, seed_user, login_as):
    a = seed_user(username="playera", role="annotator")
    b = seed_user(username="playerb", role="annotator")

    login_as(a)
    keys_a = [q["key"] for q in client.get("/api/v1/annotate/quests/me").json()["quests"]]
    login_as(b)
    keys_b = [q["key"] for q in client.get("/api/v1/annotate/quests/me").json()["quests"]]

    assert keys_a == keys_b


# ------------------------- progress: confirmed-only -------------------------


def test_progress_ignores_unreviewed_and_out_of_window_work(client, dataset, ann, login_as, monkeypatch):
    from src import config

    monkeypatch.setattr(config, "QUEST_COUNT_PER_DAY", len(CATALOG))

    imgs = dataset["images"]
    pending = _vote(client, imgs[0], imgs[1], no_overlap=False)  # left unreviewed
    approved_in_window = _vote(client, imgs[1], imgs[2], no_overlap=False)
    approved_out_of_window = _vote(client, imgs[2], imgs[3], no_overlap=False)

    login_as(dataset["scientist"])
    _review_candidate(client, approved_in_window, "approve")
    _review_candidate(client, approved_out_of_window, "approve")
    _set_reviewed_at(client, approved_out_of_window, reviewed_at=1)  # far in the past

    login_as(ann)
    quests = {q["key"]: q for q in client.get("/api/v1/annotate/quests/me").json()["quests"]}
    quest = quests[OVERLAPS_QUEST_KEY]
    # Only `approved_in_window` counts: `pending` is unreviewed, `approved_out_of_window`
    # was confirmed outside today's window.
    assert quest["progress"] == 1
    assert quest["completed"] is False


# ------------------------- claiming -------------------------


def test_claim_before_target_is_409(client, dataset, ann, login_as, monkeypatch):
    from src import config

    monkeypatch.setattr(config, "QUEST_COUNT_PER_DAY", len(CATALOG))
    resp = client.post(f"/api/v1/annotate/quests/{OVERLAPS_QUEST_KEY}/claim")
    assert resp.status_code == 409, resp.text


def test_claim_unknown_key_is_404(client, dataset, ann):
    resp = client.post("/api/v1/annotate/quests/not-a-real-quest/claim")
    assert resp.status_code == 404, resp.text


def test_claim_grants_exp_once_then_rejects_second_claim(client, dataset, ann, login_as, monkeypatch):
    from src import config

    monkeypatch.setattr(config, "QUEST_COUNT_PER_DAY", len(CATALOG))
    _complete_overlaps_quest(client, dataset, ann, login_as)

    quests = {q["key"]: q for q in client.get("/api/v1/annotate/quests/me").json()["quests"]}
    quest = quests[OVERLAPS_QUEST_KEY]
    assert quest["completed"] is True
    assert quest["claimed"] is False

    exp_before = client.get("/api/v1/auth/me").json()["exp"]
    resp = client.post(f"/api/v1/annotate/quests/{OVERLAPS_QUEST_KEY}/claim")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["quest"]["claimed"] is True
    assert body["exp"] == exp_before + quest["reward_exp"]

    # Reflected on the next fetch, and XP is only granted once.
    quests_after = {q["key"]: q for q in client.get("/api/v1/annotate/quests/me").json()["quests"]}
    assert quests_after[OVERLAPS_QUEST_KEY]["claimed"] is True

    second = client.post(f"/api/v1/annotate/quests/{OVERLAPS_QUEST_KEY}/claim")
    assert second.status_code == 409, second.text
    assert client.get("/api/v1/auth/me").json()["exp"] == body["exp"]


def test_claim_requires_authentication(client, dataset):
    client.cookies.clear()  # `dataset` leaves the client logged in as the scientist
    resp = client.post(f"/api/v1/annotate/quests/{OVERLAPS_QUEST_KEY}/claim")
    assert resp.status_code == 401, resp.text
