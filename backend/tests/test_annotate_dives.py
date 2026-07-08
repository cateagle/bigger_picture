import uuid

import pytest


def _new_uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def scientist(seed_user, login_as):
    user = seed_user(username="sci", role="scientist")
    login_as(user)
    return user


@pytest.fixture
def annotator(seed_user, login_as):
    user = seed_user(username="ann", role="annotator")
    login_as(user)
    return user


def _make_region(client, title) -> str:
    region = _new_uuid()
    assert client.post("/api/v1/dataset/regions/create", json={"uuid": region, "title": title}).status_code == 201
    return region


def _make_dive(client, region, title) -> str:
    dive = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": dive, "title": title, "region": region},
    )
    assert resp.status_code == 201, resp.text
    return dive


def test_annotator_can_list_dives_for_region(client, scientist, seed_user, login_as):
    region_a = _make_region(client, "region-a")
    region_b = _make_region(client, "region-b")
    dive_a1 = _make_dive(client, region_a, "dive-a1")
    _make_dive(client, region_a, "dive-a2")
    _make_dive(client, region_b, "dive-b1")

    login_as(seed_user(username="ann", role="annotator"))

    resp = client.get(f"/api/v1/annotate/dives?region={region_a}")
    assert resp.status_code == 200
    body = resp.json()
    titles = {d["title"] for d in body["dives"]}
    assert titles == {"dive-a1", "dive-a2"}
    assert all(d["region"] == region_a for d in body["dives"])
    assert dive_a1 in {d["uuid"] for d in body["dives"]}


def test_list_dives_requires_authentication(client, scientist):
    region = _make_region(client, "region-a")
    client.cookies.clear()
    resp = client.get(f"/api/v1/annotate/dives?region={region}")
    assert resp.status_code == 401


def test_list_dives_empty_region(client, scientist, seed_user, login_as):
    region = _make_region(client, "empty-region")
    login_as(seed_user(username="ann", role="annotator"))

    resp = client.get(f"/api/v1/annotate/dives?region={region}")
    assert resp.status_code == 200
    assert resp.json() == {"dives": []}


def test_list_dives_unknown_region_is_404(client, annotator):
    resp = client.get(f"/api/v1/annotate/dives?region={_new_uuid()}")
    assert resp.status_code == 404
