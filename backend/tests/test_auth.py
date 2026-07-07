from src import config


def test_signup_creates_annotator_and_sets_cookie(client):
    response = client.post("/api/v1/auth/signup", json={"username": "alice"})
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["role"] == "annotator"
    assert config.COOKIE_NAME in response.cookies


def test_signup_duplicate_username_conflicts(client):
    client.post("/api/v1/auth/signup", json={"username": "bob"})
    response = client.post("/api/v1/auth/signup", json={"username": "bob"})
    assert response.status_code == 409


def test_signup_duplicate_username_case_insensitive(client):
    client.post("/api/v1/auth/signup", json={"username": "Carl"})
    response = client.post("/api/v1/auth/signup", json={"username": "carl"})
    assert response.status_code == 409


def test_me_without_cookie_is_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_resolves_signed_up_identity(client):
    signup_response = client.post("/api/v1/auth/signup", json={"username": "dana"})
    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "dana"
    assert me_response.json()["id"] == signup_response.json()["id"]


def test_me_with_garbage_cookie_is_401(client):
    client.cookies.set(config.COOKIE_NAME, "not-a-valid-uuid")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout_clears_cookie(client):
    client.post("/api/v1/auth/signup", json={"username": "erin"})
    assert client.get("/api/v1/auth/me").status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401
