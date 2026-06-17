"""Module de base de données pour service-monde (Adaptateur Luanti).

Ce service n'utilise PAS SQLite ni d'ORM. Il lit en LECTURE SEULE la base
PostgreSQL du serveur Luanti en utilisant du SQL explicite.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# L'URI de la base PostgreSQL (typiquement fournie par le docker-compose)
DB_URI = os.environ.get("DB_URI", "postgresql://postgres:postgres@luanti-db:5432/postgres")

def get_connection():
    """Ouvre et retourne une connexion à la base de données Luanti."""
    # On utilise RealDictCursor pour que fetchall() retourne des dictionnaires
    # directement sérialisables en JSON par Flask.
    return psycopg2.connect(DB_URI, cursor_factory=RealDictCursor)