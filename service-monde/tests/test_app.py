from datetime import datetime
from decimal import Decimal

import pytest

import app as monde


@pytest.fixture()
def client():
    monde.app.config.update(TESTING=True)
    return monde.app.test_client()


def test_health(client, monkeypatch):
    monkeypatch.setattr(monde.db, "ping", lambda: None)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "monde", "database": "ok"}


def test_health_returns_503_when_database_is_down(client, monkeypatch):
    def fail():
        raise monde.db.DatabaseUnavailable("base Luanti indisponible")

    monkeypatch.setattr(monde.db, "ping", fail)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json() == {"erreur": "base Luanti indisponible"}


def test_list_players(client, monkeypatch):
    monkeypatch.setattr(
        monde.db,
        "query_all",
        lambda *_args, **_kwargs: [
            {"pseudo": "alice", "last_login": 1_700_000_000, "privileges": ["interact", "shout"]},
            {"pseudo": "bob", "last_login": 0, "privileges": []},
        ],
    )
    response = client.get("/joueurs")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0]["pseudo"] == "alice"
    assert payload[0]["derniere_connexion"].endswith("Z")
    assert payload[1]["derniere_connexion"] is None


def test_unknown_player_returns_404(client, monkeypatch):
    monkeypatch.setattr(monde.db, "query_one", lambda *_args, **_kwargs: None)
    response = client.get("/joueurs/inconnu")
    assert response.status_code == 404
    assert response.get_json() == {"erreur": "joueur inconnu"}


def test_position_payload(client, monkeypatch):
    monkeypatch.setattr(
        monde.db,
        "query_one",
        lambda *_args, **_kwargs: {
            "pseudo": "alice",
            "posx": Decimal("12.5"),
            "posy": Decimal("8.0"),
            "posz": Decimal("-2.25"),
            "hp": 20,
            "breath": 10,
            "modification_date": datetime(2026, 6, 17, 8, 30),
        },
    )
    response = client.get("/positions/alice")
    assert response.status_code == 200
    assert response.get_json() == {
        "pseudo": "alice",
        "x": 12.5,
        "y": 8,
        "z": -2.25,
        "hp": 20,
        "souffle": 10,
        "vivant": True,
        "derniere_sauvegarde": "2026-06-17T08:30:00Z",
    }


def test_inventory_is_grouped_by_luanti_inventory(client, monkeypatch):
    monkeypatch.setattr(monde.db, "query_one", lambda *_args, **_kwargs: {"existe": True})
    monkeypatch.setattr(
        monde.db,
        "query_all",
        lambda *_args, **_kwargs: [
            {"inv_id": 1, "inv_name": "main", "inv_width": 8, "inv_size": 32, "slot_id": 0, "item": "default:stone 12"},
            {"inv_id": 1, "inv_name": "main", "inv_width": 8, "inv_size": 32, "slot_id": 1, "item": ""},
            {"inv_id": 2, "inv_name": "craft", "inv_width": 3, "inv_size": 9, "slot_id": None, "item": None},
        ],
    )
    response = client.get("/joueurs/alice/inventaire")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["pseudo"] == "alice"
    assert payload["inventaires"][0]["nom"] == "main"
    assert payload["inventaires"][0]["objets"][0] == {"slot": 0, "item": "default:stone 12"}
    assert payload["inventaires"][1]["objets"] == []
