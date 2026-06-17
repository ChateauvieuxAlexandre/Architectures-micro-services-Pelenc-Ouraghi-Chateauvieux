"""Tests pytest du service-classements (bonus)."""
import os
import importlib

import jwt
import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    import db
    import app
    import auth

    importlib.reload(auth)
    importlib.reload(db)
    importlib.reload(app)

    app.app.config["TESTING"] = True
    with app.app.test_client() as c:
        yield c


def token(pseudo="maxime", roles=None):
    roles = roles if roles is not None else ["joueur"]
    return jwt.encode({"pseudo": pseudo, "roles": roles}, "test-secret", algorithm="HS256")


def auth_header(pseudo="maxime", roles=None):
    return {"Authorization": f"Bearer {token(pseudo, roles)}"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_ajoute_score_sans_jeton(client):
    r = client.post("/scores", json={"pseudo": "maxime", "points": 10})
    assert r.status_code == 401


def test_ajoute_score_points_invalides(client):
    r = client.post("/scores", json={"pseudo": "maxime", "points": -5}, headers=auth_header())
    assert r.status_code == 400

    r = client.post("/scores", json={"pseudo": "maxime", "points": "dix"}, headers=auth_header())
    assert r.status_code == 400


def test_ajoute_score_cumule(client):
    r1 = client.post("/scores", json={"pseudo": "maxime", "points": 10}, headers=auth_header())
    assert r1.status_code == 201
    assert r1.get_json()["points"] == 10

    r2 = client.post("/scores", json={"pseudo": "maxime", "points": 10}, headers=auth_header())
    assert r2.status_code == 201
    assert r2.get_json()["points"] == 20


def test_score_inconnu_404(client):
    r = client.get("/scores/inconnu")
    assert r.status_code == 404


def test_classement_trie(client):
    client.post("/scores", json={"pseudo": "alice", "points": 5}, headers=auth_header())
    client.post("/scores", json={"pseudo": "bob", "points": 50}, headers=auth_header())

    r = client.get("/classement")
    assert r.status_code == 200
    pseudos = [j["pseudo"] for j in r.get_json()]
    assert pseudos[0] == "bob"
    assert pseudos[1] == "alice"


def test_classement_top(client):
    client.post("/scores", json={"pseudo": "alice", "points": 5}, headers=auth_header())
    client.post("/scores", json={"pseudo": "bob", "points": 50}, headers=auth_header())

    r = client.get("/classement/top/1")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["pseudo"] == "bob"


def test_classement_pagination(client):
    for pseudo, points in [("a", 1), ("b", 2), ("c", 3)]:
        client.post("/scores", json={"pseudo": pseudo, "points": points}, headers=auth_header())

    r = client.get("/classement?page=1&taille=2")
    assert r.status_code == 200
    assert len(r.get_json()) == 2

    r2 = client.get("/classement?page=2&taille=2")
    assert r2.status_code == 200
    assert len(r2.get_json()) == 1


def test_classement_periode_invalide(client):
    r = client.get("/classement/periode/mois")
    assert r.status_code == 400


def test_classement_periode_jour(client):
    client.post("/scores", json={"pseudo": "maxime", "points": 10}, headers=auth_header())
    r = client.get("/classement/periode/jour")
    assert r.status_code == 200
    data = r.get_json()
    assert data[0]["pseudo"] == "maxime"
    assert data[0]["points"] == 10


def test_badges(client):
    client.post("/scores", json={"pseudo": "maxime", "points": 150}, headers=auth_header())
    r = client.get("/badges/maxime")
    assert r.status_code == 200
    noms = [b["nom"] for b in r.get_json()["badges"]]
    assert "bronze" in noms
    assert "argent" not in noms


def test_badges_inconnu(client):
    r = client.get("/badges/inconnu")
    assert r.status_code == 404
