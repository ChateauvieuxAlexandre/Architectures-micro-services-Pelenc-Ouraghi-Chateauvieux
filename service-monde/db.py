"""Accès en lecture seule à la base PostgreSQL du serveur Luanti."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import psycopg2
from psycopg2.extras import RealDictCursor

LUANTI_DSN = os.environ.get(
    "LUANTI_DSN",
    "host=localhost port=5432 dbname=luanti user=monde_reader password=monde_reader",
)


class DatabaseUnavailable(RuntimeError):
    """La base Luanti ne peut pas être jointe ou interrogée."""


@contextmanager
def connection() -> Iterator[psycopg2.extensions.connection]:
    """Ouvre une connexion explicitement limitée à la lecture."""
    try:
        conn = psycopg2.connect(LUANTI_DSN, connect_timeout=3)
        conn.set_session(readonly=True, autocommit=True)
    except psycopg2.Error as exc:
        raise DatabaseUnavailable("base Luanti indisponible") from exc

    try:
        yield conn
    finally:
        conn.close()


def query_all(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    try:
        with connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params or ())
            return [dict(row) for row in cursor.fetchall()]
    except DatabaseUnavailable:
        raise
    except psycopg2.Error as exc:
        raise DatabaseUnavailable("erreur lors de la lecture de la base Luanti") from exc


def query_one(sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    try:
        with connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params or ())
            row = cursor.fetchone()
            return dict(row) if row is not None else None
    except DatabaseUnavailable:
        raise
    except psycopg2.Error as exc:
        raise DatabaseUnavailable("erreur lors de la lecture de la base Luanti") from exc


def ping() -> None:
    query_one("SELECT 1 AS ok")
