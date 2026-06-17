"""Tests pour la fonction inscrire_evenement.

Utilise pytest et le client de test de Flask.
"""
import pytest
import json
from app import app
import db


@pytest.fixture
def client():
    """Crée un client de test et initialise la base."""
    app.config["TESTING"] = True
    
    with app.test_client() as client:
        # Initialiser la base de données
        db.init()
        yield client


@pytest.fixture
def token_joueur():
    """Génère un JWT valide pour un joueur."""
    from auth import create_jwt
    return create_jwt({"pseudo": "joueur_test", "roles": ["joueur"]})


@pytest.fixture
def token_admin():
    """Génère un JWT valide pour un admin."""
    from auth import create_jwt
    return create_jwt({"pseudo": "admin_test", "roles": ["admin"]})


@pytest.fixture
def setup_evenement(token_admin):
    """Crée un événement de test."""
    with app.test_client() as client:
        response = client.post(
            "/",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={
                "nom": "Événement Test",
                "cordx": 100.0,
                "cordy": 200.0,
                "cordz": 300.0,
                "nb_places": 10,
                "date": "2026-07-01",
                "statut": "ouvert"
            }
        )
        return response


def test_inscrire_evenement_succes(client, token_joueur, setup_evenement, token_admin):
    """Test d'une inscription réussie."""
    # D'abord créer un événement
    response_create = client.post(
        "/",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={
            "nom": "Événement Test",
            "cordx": 100.0,
            "cordy": 200.0,
            "cordz": 300.0,
            "nb_places": 10,
            "date": "2026-07-01",
            "statut": "ouvert"
        }
    )
    
    # Ensuite s'inscrire
    response = client.post(
        "/1/inscription",
        headers={"Authorization": f"Bearer {token_joueur}"}
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert "message" in data


def test_inscrire_evenement_inexistant(client, token_joueur):
    """Test d'inscription à un événement inexistant."""
    response = client.post(
        "/999/inscription",
        headers={"Authorization": f"Bearer {token_joueur}"}
    )
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert "erreur" in data


def test_inscrire_evenement_doublon(client, token_joueur, token_admin):
    """Test d'une double inscription."""
    # Créer un événement
    client.post(
        "/",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={
            "nom": "Événement Test",
            "cordx": 100.0,
            "cordy": 200.0,
            "cordz": 300.0,
            "nb_places": 10,
            "date": "2026-07-01",
            "statut": "ouvert"
        }
    )
    
    # Première inscription
    response1 = client.post(
        "/1/inscription",
        headers={"Authorization": f"Bearer {token_joueur}"}
    )
    assert response1.status_code == 201
    
    # Deuxième inscription (doublon)
    response2 = client.post(
        "/1/inscription",
        headers={"Authorization": f"Bearer {token_joueur}"}
    )
    
    assert response2.status_code == 409
    data = json.loads(response2.data)
    assert "erreur" in data


def test_inscrire_evenement_sans_auth(client):
    """Test d'inscription sans authentification."""
    response = client.post("/1/inscription")
    
    assert response.status_code == 401  # Unauthorized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
