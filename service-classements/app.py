"""Squelette minimal d'un micro-service Voxenfer (à copier et adapter).

Auteur : Philippe ROUSSILLE <roussille@3il.fr>

Vous avez tout vu aux TP 08 à 12 : Flask + routes REST/JSON avec les bons codes,
JWT (auth.py), /health et /metrics, une base propre au service via un ORM (db.py).
Ce fichier ne donne QUE la charpente : à vous d'écrire les routes de votre domaine
(voir 2-contrats.md pour celles qu'on attend de votre service).
"""
from datetime import datetime, timedelta, timezone

from flask import Flask, request, jsonify
from sqlalchemy import func

import db
from auth import require_jwt, require_role  # à compléter dans auth.py ; protège vos écritures

app = Flask(__name__)
db.init()

# Bonus : seuils de points -> badges
BADGES = [
    (100, "bronze"),
    (500, "argent"),
    (1000, "or"),
]

_metriques = {"requetes": 0}


@app.before_request
def _compter():
    _metriques["requetes"] += 1


# --- Observabilité (à garder tel quel) ------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "service-classements"})


@app.route("/metrics")
def metrics():
    return jsonify({"requetes_total": _metriques["requetes"]})


# --- Votre domaine ----------------------------------------------------------

@app.route("/classement")
def classement():
    page = request.args.get("page", type=int)
    taille = request.args.get("taille", type=int)

    with db.Session() as s:
        requete = s.query(db.Score).order_by(db.Score.points.desc())

        # Bonus : pagination si page/taille fournis (sinon comportement de base inchangé)
        if page is not None or taille is not None:
            page = page if page and page > 0 else 1
            taille = taille if taille and taille > 0 else 10
            requete = requete.offset((page - 1) * taille).limit(taille)

        scores = requete.all()
        return jsonify([{"pseudo": sc.pseudo, "points": sc.points} for sc in scores])


@app.route("/classement/top/<int:n>")
def classement_top(n):
    with db.Session() as s:
        scores = (
            s.query(db.Score)
            .order_by(db.Score.points.desc())
            .limit(n)
            .all()
        )
        return jsonify([{"pseudo": sc.pseudo, "points": sc.points} for sc in scores])


@app.route("/classement/periode/<periode>")
def classement_periode(periode):
    """Bonus : classement restreint aux points gagnés sur une période (jour/semaine)."""
    if periode == "jour":
        depuis = datetime.now(timezone.utc) - timedelta(days=1)
    elif periode == "semaine":
        depuis = datetime.now(timezone.utc) - timedelta(weeks=1)
    else:
        return jsonify({"erreur": "periode invalide (jour ou semaine)"}), 400

    with db.Session() as s:
        resultats = (
            s.query(db.Gain.pseudo, func.sum(db.Gain.points).label("points"))
            .filter(db.Gain.horodatage >= depuis)
            .group_by(db.Gain.pseudo)
            .order_by(func.sum(db.Gain.points).desc())
            .all()
        )
        return jsonify([{"pseudo": pseudo, "points": points} for pseudo, points in resultats])


@app.route("/badges/<pseudo>")
def badges(pseudo):
    """Bonus : badges obtenus par un joueur selon des seuils de points."""
    with db.Session() as s:
        sc = s.query(db.Score).filter_by(pseudo=pseudo).first()
        if sc is None:
            return jsonify({"erreur": "pseudo inconnu"}), 404
        obtenus = [{"seuil": seuil, "nom": nom} for seuil, nom in BADGES if sc.points >= seuil]
        return jsonify({"pseudo": pseudo, "points": sc.points, "badges": obtenus})


@app.route("/scores/<pseudo>")
def score(pseudo):
    with db.Session() as s:
        sc = s.query(db.Score).filter_by(pseudo=pseudo).first()
        if sc is None:
            return jsonify({"erreur": "pseudo inconnu"}), 404
        return jsonify({"pseudo": sc.pseudo, "points": sc.points})


@app.route("/scores", methods=["POST"])
@require_jwt
def ajouter_score():
    payload = request.get_json(silent=True) or {}
    pseudo = payload.get("pseudo")
    points = payload.get("points")
    if not isinstance(pseudo, str) or not pseudo:
        return jsonify({"erreur": "pseudo invalide"}), 400
    if not isinstance(points, int) or isinstance(points, bool) or points < 0:
        return jsonify({"erreur": "points invalide"}), 400

    with db.Session() as s:
        sc = s.query(db.Score).filter_by(pseudo=pseudo).first()
        if sc is None:
            sc = db.Score(pseudo=pseudo, points=points)
            s.add(sc)
        else:
            sc.points += points
        s.add(db.Gain(pseudo=pseudo, points=points))  # historique pour le bonus "par période"
        s.commit()
        return jsonify({"pseudo": sc.pseudo, "points": sc.points}), 201


if __name__ == "__main__":
    # 0.0.0.0 : indispensable en conteneur. Port interne uniforme : 5000.
    app.run(host="0.0.0.0", port=5000)
