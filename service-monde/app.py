"""Micro-service Voxenfer : service-monde (G1).

Adaptateur en lecture seule sur la base PostgreSQL de Luanti.
Toutes les routes sont ouvertes (rien à protéger).
"""
from flask import Flask, jsonify
import db

app = Flask(__name__)

_metriques = {"requetes": 0}

@app.before_request
def _compter():
    _metriques["requetes"] += 1

# --- Observabilité --------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "service-monde"})


@app.route("/metrics")
def metrics():
    return jsonify({"requetes_total": _metriques["requetes"]})


# --- Domaine : service-monde (Lectures Luanti) ----------------------------

@app.route("/joueurs", methods=["GET"])
def get_joueurs():
    """Renvoie la liste des joueurs enregistrés et leurs privilèges."""
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT a.name AS pseudo, a.last_login AS derniere_connexion,
                   string_agg(p.privilege, ', ') AS privileges
            FROM auth a
            LEFT JOIN user_privileges p ON a.name = p.name
            GROUP BY a.name, a.last_login
        """)
        joueurs = cur.fetchall()
        return jsonify(joueurs), 200
    finally:
        cur.close()
        conn.close()


@app.route("/joueurs/<pseudo>", methods=["GET"])
def get_joueur(pseudo):
    """Renvoie la fiche d'un joueur enregistré (404 si inconnu)."""
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT a.name AS pseudo, a.last_login AS derniere_connexion,
                   string_agg(p.privilege, ', ') AS privileges
            FROM auth a
            LEFT JOIN user_privileges p ON a.name = p.name
            WHERE a.name = %s
            GROUP BY a.name, a.last_login
        """, (pseudo,))
        joueur = cur.fetchone()

        if not joueur:
            return jsonify({"erreur": "Joueur inconnu"}), 404

        return jsonify(joueur), 200
    finally:
        cur.close()
        conn.close()


@app.route("/positions/<pseudo>", methods=["GET"])
def get_position(pseudo):
    """Renvoie la dernière position/hp/vivant du joueur (404 si jamais joué)."""
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT posx, posy, posz, hp, breath
            FROM player
            WHERE name = %s
        """, (pseudo,))
        pos = cur.fetchone()

        if not pos:
            return jsonify({"erreur": "Joueur n'a jamais joué (aucune position sauvegardée)"}), 404

        # Un joueur est considéré comme vivant si ses HP sont supérieurs à 0
        pos["vivant"] = pos.get("hp", 0) > 0
        return jsonify(pos), 200
    finally:
        cur.close()
        conn.close()


@app.route("/joueurs/<pseudo>/inventaire", methods=["GET"])
def get_inventaire(pseudo):
    """Renvoie l'inventaire sauvegardé du joueur."""
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT i.inv_id, i.inv_name, it.item_name, it.count
            FROM player_inventories i
            JOIN player_inventory_items it ON i.inv_id = it.inv_id
            WHERE i.name = %s
        """, (pseudo,))
        items = cur.fetchall()
        return jsonify(items), 200
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)