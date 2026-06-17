"""Service-monde Voxenfer : adaptateur HTTP en lecture seule sur PostgreSQL/Luanti."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock
from typing import Any

from flask import Flask, jsonify, send_from_directory

import db

app = Flask(__name__)

_metrics = {
    "requetes_total": 0,
    "erreurs_base_total": 0,
    "reponses_404_total": 0,
}
_metrics_lock = Lock()


@app.before_request
def count_request() -> None:
    with _metrics_lock:
        _metrics["requetes_total"] += 1


def _iso_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


def _last_login(value: Any) -> str | None:
    if value in (None, 0, "0"):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError):
        return None


def _number(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _not_found(message: str):
    with _metrics_lock:
        _metrics["reponses_404_total"] += 1
    return jsonify({"erreur": message}), 404


@app.errorhandler(db.DatabaseUnavailable)
def database_unavailable(exc: db.DatabaseUnavailable):
    with _metrics_lock:
        _metrics["erreurs_base_total"] += 1
    return jsonify({"erreur": str(exc)}), 503


@app.errorhandler(404)
def route_not_found(_exc):
    return _not_found("route inconnue")


@app.get("/health")
def health():
    db.ping()
    return jsonify({"status": "ok", "service": "monde", "database": "ok"})


@app.get("/metrics")
def metrics():
    with _metrics_lock:
        snapshot = dict(_metrics)
    return jsonify(snapshot)


@app.get("/joueurs")
def list_players():
    rows = db.query_all(
        """
        SELECT
            a.name AS pseudo,
            a.last_login,
            COALESCE(
                array_agg(up.privilege ORDER BY up.privilege)
                    FILTER (WHERE up.privilege IS NOT NULL),
                ARRAY[]::text[]
            ) AS privileges
        FROM auth AS a
        LEFT JOIN user_privileges AS up ON up.id = a.id
        GROUP BY a.id, a.name, a.last_login
        ORDER BY lower(a.name), a.name
        """
    )
    return jsonify(
        [
            {
                "pseudo": row["pseudo"],
                "derniere_connexion": _last_login(row.get("last_login")),
                "privileges": row.get("privileges") or [],
            }
            for row in rows
        ]
    )


@app.get("/joueurs/<string:pseudo>")
def get_player(pseudo: str):
    row = db.query_one(
        """
        SELECT
            a.name AS pseudo,
            a.last_login,
            COALESCE(
                array_agg(up.privilege ORDER BY up.privilege)
                    FILTER (WHERE up.privilege IS NOT NULL),
                ARRAY[]::text[]
            ) AS privileges,
            p.name IS NOT NULL AS a_joue,
            p.creation_date,
            p.modification_date,
            p.posx,
            p.posy,
            p.posz,
            p.hp,
            p.breath
        FROM auth AS a
        LEFT JOIN user_privileges AS up ON up.id = a.id
        LEFT JOIN player AS p ON p.name = a.name
        WHERE a.name = %s
        GROUP BY
            a.id, a.name, a.last_login,
            p.name, p.creation_date, p.modification_date,
            p.posx, p.posy, p.posz, p.hp, p.breath
        """,
        (pseudo,),
    )
    if row is None:
        return _not_found("joueur inconnu")

    response: dict[str, Any] = {
        "pseudo": row["pseudo"],
        "derniere_connexion": _last_login(row.get("last_login")),
        "privileges": row.get("privileges") or [],
        "a_joue": bool(row.get("a_joue")),
    }
    if response["a_joue"]:
        hp = int(row["hp"])
        response.update(
            {
                "creation": _iso_datetime(row.get("creation_date")),
                "derniere_sauvegarde": _iso_datetime(row.get("modification_date")),
                "position": {
                    "x": _number(row.get("posx")),
                    "y": _number(row.get("posy")),
                    "z": _number(row.get("posz")),
                },
                "hp": hp,
                "souffle": int(row["breath"]),
                "vivant": hp > 0,
            }
        )
    return jsonify(response)


@app.get("/positions")
def list_positions():
    rows = db.query_all(
        """
        SELECT name AS pseudo, posx, posy, posz, hp, breath, modification_date
        FROM player
        ORDER BY lower(name), name
        """
    )
    return jsonify([_position_payload(row) for row in rows])


def _position_payload(row: dict[str, Any]) -> dict[str, Any]:
    hp = int(row["hp"])
    return {
        "pseudo": row["pseudo"],
        "x": _number(row.get("posx")),
        "y": _number(row.get("posy")),
        "z": _number(row.get("posz")),
        "hp": hp,
        "souffle": int(row["breath"]),
        "vivant": hp > 0,
        "derniere_sauvegarde": _iso_datetime(row.get("modification_date")),
    }


@app.get("/positions/<string:pseudo>")
def get_position(pseudo: str):
    row = db.query_one(
        """
        SELECT name AS pseudo, posx, posy, posz, hp, breath, modification_date
        FROM player
        WHERE name = %s
        """,
        (pseudo,),
    )
    if row is None:
        return _not_found("aucune position sauvegardee pour ce joueur")
    return jsonify(_position_payload(row))


@app.get("/joueurs/<string:pseudo>/inventaire")
def get_inventory(pseudo: str):
    exists = db.query_one(
        """
        SELECT EXISTS(
            SELECT 1 FROM auth WHERE name = %s
            UNION ALL
            SELECT 1 FROM player WHERE name = %s
        ) AS existe
        """,
        (pseudo, pseudo),
    )
    if not exists or not exists.get("existe"):
        return _not_found("joueur inconnu")

    rows = db.query_all(
        """
        SELECT
            i.inv_id,
            i.inv_name,
            i.inv_width,
            i.inv_size,
            it.slot_id,
            it.item
        FROM player_inventories AS i
        LEFT JOIN player_inventory_items AS it
            ON it.player = i.player AND it.inv_id = i.inv_id
        WHERE i.player = %s
        ORDER BY i.inv_id, it.slot_id
        """,
        (pseudo,),
    )

    inventories: list[dict[str, Any]] = []
    by_id: dict[int, dict[str, Any]] = {}
    for row in rows:
        inv_id = int(row["inv_id"])
        inventory = by_id.get(inv_id)
        if inventory is None:
            inventory = {
                "id": inv_id,
                "nom": row.get("inv_name") or "",
                "largeur": int(row["inv_width"]),
                "taille": int(row["inv_size"]),
                "objets": [],
            }
            by_id[inv_id] = inventory
            inventories.append(inventory)

        if row.get("slot_id") is not None:
            inventory["objets"].append(
                {
                    "slot": int(row["slot_id"]),
                    "item": row.get("item") or "",
                }
            )

    return jsonify({"pseudo": pseudo, "inventaires": inventories})


@app.get("/carte")
def map_page():
    return send_from_directory(app.static_folder, "carte.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
