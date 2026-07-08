import uuid

import pytest


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


def _new_uuid() -> str:
    return str(uuid.uuid4())


def test_annotator_can_list_regions(client, scientist, seed_user, login_as):
    u1 = _new_uuid()
    mesh = {"type": "Polygon", "coordinates": [[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [1.0, 2.0]]]}
    client.post(
        "/api/v1/dataset/regions/create",
        json={"uuid": u1, "title": "meshed reef", "metadata": {"mesh": mesh}},
    )
    u2 = _new_uuid()
    client.post("/api/v1/dataset/regions/create", json={"uuid": u2, "title": "plain reef"})

    # Switch the session to a plain annotator only after the regions above
    # have been created as the scientist.
    login_as(seed_user(username="ann", role="annotator"))

    resp = client.get("/api/v1/annotate/regions")
    assert resp.status_code == 200
    body = resp.json()
    titles = {r["title"]: r for r in body["regions"]}
    assert set(titles) == {"meshed reef", "plain reef"}
    assert titles["meshed reef"]["metadata"] == {"mesh": mesh}
    assert titles["plain reef"]["metadata"] is None


def test_list_regions_requires_authentication(client):
    resp = client.get("/api/v1/annotate/regions")
    assert resp.status_code == 401


def test_list_regions_empty(client, annotator):
    resp = client.get("/api/v1/annotate/regions")
    assert resp.status_code == 200
    assert resp.json() == {"regions": []}
