"""Squelette minimal d'un micro-service Voxenfer (à copier et adapter).

Auteur : Philippe ROUSSILLE <roussille@3il.fr>

Vous avez tout vu aux TP 08 à 12 : Flask + routes REST/JSON avec les bons codes,
JWT (auth.py), /health et /metrics, une base propre au service via un ORM (db.py).
Ce fichier ne donne QUE la charpente : à vous d'écrire les routes de votre domaine
(voir 2-contrats.md pour celles qu'on attend de votre service).
"""
import os

import requests
from flask import Flask, request, jsonify

import db
from auth import require_jwt, require_role

ECONOMIE_URL = os.environ.get("ECONOMIE_URL", "http://service-economie:5000")

app = Flask(__name__)
db.init()

_metriques = {"requetes": 0}


@app.before_request
def _compter():
    _metriques["requetes"] += 1


# --- Observabilité (à garder tel quel) ------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "Boutique"})


@app.route("/metrics")
def metrics():
    return jsonify({"requetes_total": _metriques["requetes"]})



# --- Catalogue ----------------------------------------------------------------

@app.route("/objets", methods=["GET"])
def lister_objets():
    with db.Session() as s:
        objets = s.query(db.Objet).all()
        return jsonify([
            {"id": o.id, "nom": o.nom, "prix": o.prix, "item": o.item}
            for o in objets
        ])


@app.route("/objets", methods=["POST"])
@require_role("admin")
def creer_objet():
    data = request.get_json() or {}
    if not all(k in data for k in ("nom", "prix", "item")):
        return jsonify({"erreur": "champs requis : nom, prix, item"}), 400
    if not isinstance(data["prix"], int) or data["prix"] <= 0:
        return jsonify({"erreur": "prix doit être un entier positif"}), 400
    with db.Session() as s:
        objet = db.Objet(nom=data["nom"], prix=data["prix"], item=data["item"])
        s.add(objet)
        s.commit()
        return jsonify({"id": objet.id, "nom": objet.nom, "prix": objet.prix, "item": objet.item}), 201


# --- File de livraisons -------------------------------------------------------

@app.route("/livraisons", methods=["GET"])
@require_role("admin")
def lister_livraisons():
    with db.Session() as s:
        livraisons = s.query(db.Livraison).filter_by(statut="en_attente").all()
        return jsonify([
            {"id": l.id, "type": l.type, "cible": l.cible, "objet": l.objet}
            for l in livraisons
        ])


@app.route("/livraisons/<int:livraison_id>/fait", methods=["POST"])
@require_role("admin")
def acquitter_livraison(livraison_id):
    with db.Session() as s:
        livraison = s.get(db.Livraison, livraison_id)
        if livraison is None:
            return jsonify({"erreur": "livraison introuvable"}), 404
        livraison.statut = "livre"
        s.commit()
        return jsonify({"message": "livraison acquittée", "id": livraison_id})


# --- Inventaire joueur --------------------------------------------------------

@app.route("/inventaire/<pseudo>", methods=["GET"])
@require_jwt
def inventaire(pseudo):
    with db.Session() as s:
        livraisons = s.query(db.Livraison).filter_by(cible=pseudo, statut="livre").all()
        return jsonify([{"objet": l.objet} for l in livraisons])


# --- Achat --------------------------------------------------------------------

@app.route("/acheter", methods=["POST"])
@require_jwt
def acheter():
    pseudo = request.joueur["pseudo"]
    data = request.get_json() or {}
    if "objet_id" not in data:
        return jsonify({"erreur": "champ requis : objet_id"}), 400

    if not isinstance(data["objet_id"], int) or isinstance(data["objet_id"], bool):
        return jsonify({"erreur": "objet_id doit être un entier"}), 400

    with db.Session() as s:
        objet = s.get(db.Objet, data["objet_id"])
        if objet is None:
            return jsonify({"erreur": "objet introuvable"}), 404

        try:
            headers = {"Authorization": request.headers.get("Authorization")}
            reponse = requests.post(
                f"{ECONOMIE_URL}/debiter",
                json={"pseudo": pseudo, "montant": objet.prix},
                headers=headers,
                timeout=5,
            )
        except requests.exceptions.RequestException:
            return jsonify({"erreur": "service économie injoignable, réessayez"}), 503

        if reponse.status_code == 409:
            return jsonify({"erreur": "solde insuffisant"}), 409
        if reponse.status_code != 200:
            return jsonify({"erreur": "erreur inattendue côté économie"}), 503

        livraison = db.Livraison(
            cible=pseudo,
            objet=objet.item,
            statut="en_attente",
        )
        s.add(livraison)
        s.commit()
        return jsonify({"message": "achat validé", "livraison_id": livraison.id}), 201



if __name__ == "__main__":
    # 0.0.0.0 : indispensable en conteneur. Port interne uniforme : 5000.
    app.run(host="0.0.0.0", port=5000)
