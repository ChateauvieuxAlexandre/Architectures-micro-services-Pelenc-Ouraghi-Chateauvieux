"""Squelette minimal d'un micro-service Voxenfer (à copier et adapter).

Auteur : Philippe ROUSSILLE <roussille@3il.fr>

Vous avez tout vu aux TP 08 à 12 : Flask + routes REST/JSON avec les bons codes,
JWT (auth.py), /health et /metrics, une base propre au service via un ORM (db.py).
Ce fichier ne donne QUE la charpente : à vous d'écrire les routes de votre domaine
(voir 2-contrats.md pour celles qu'on attend de votre service).
"""
from flask import Flask, request, jsonify

import db
from auth import require_jwt, require_role  # à compléter dans auth.py ; protège vos écritures

app = Flask(__name__)
db.init()

_metriques = {"requetes": 0}


@app.before_request
def _compter():
    _metriques["requetes"] += 1


# --- Observabilité (à garder tel quel) ------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "moderation"})  # mettez votre nom


@app.route("/metrics")
def metrics():
    return jsonify({"requetes_total": _metriques["requetes"]})




@app.route("/signalements", methods=["POST"])
@require_jwt
def creer_signalement():
    data = request.get_json() or {}
    if "pseudo_vise" not in data or "raison" not in data:
        return jsonify({"erreur": "Champs pseudo_vise et raison obligatoires"}), 400
    with db.Session() as s:
        sig = db.Signalement(pseudo_vise=data["pseudo_vise"], raison=data["raison"])
        s.add(sig)
        s.commit()
    return jsonify({"message": "Signalement créé"}), 201


@app.route("/signalements", methods=["GET"])
@require_role("moderateur")
def lister_signalements():
    with db.Session() as s:
        sigs = s.query(db.Signalement).all()
        resultat = [{"id": sig.id, "pseudo_vise": sig.pseudo_vise, "raison": sig.raison} for sig in sigs]
        return jsonify(resultat), 200

@app.route("/bannis", methods=["POST"])
@require_role("moderateur")
def bannir_joueur():
    data = request.get_json() or {}
    if "pseudo" not in data or "motif" not in data or "duree" not in data:
        return jsonify({"erreur": "Champs pseudo, motif et duree obligatoires"}), 400
    with db.Session() as s:
        banni = s.query(db.Banni).filter_by(pseudo=data["pseudo"]).first()
        if not banni:
            banni = db.Banni(pseudo=data["pseudo"], motif=data["motif"], duree=data["duree"])
            s.add(banni)
        else:
            banni.motif = data["motif"]
            banni.duree = data["duree"]
        s.commit()
    return jsonify({"message": f"Joueur {data['pseudo']} banni"}), 201


@app.route("/bannis", methods=["GET"])
def lister_bannis():
    with db.Session() as s:
        bannis = s.query(db.Banni).all()
        resultat = [{"pseudo": b.pseudo} for b in bannis]
        return jsonify(resultat), 200

@app.route("/bannis/<pseudo>", methods=["GET"])
def verifier_banni(pseudo):
    with db.Session() as s:
        banni = s.query(db.Banni).filter_by(pseudo=pseudo).first()
        if banni:
            return jsonify({"pseudo": pseudo, "banni": True, "motif": banni.motif, "duree": banni.duree}), 200
        return jsonify({"pseudo": pseudo, "banni": False}), 200

@app.route("/bannis/<pseudo>", methods=["DELETE"])
@require_role("moderateur")
def lever_bannissement(pseudo):
    with db.Session() as s:
        banni = s.query(db.Banni).filter_by(pseudo=pseudo).first()
        if not banni:
            return jsonify({"erreur": "Joueur non banni"}), 404
        s.delete(banni)
        s.commit()
    return jsonify({"message": f"Ban levé pour {pseudo}"}), 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)