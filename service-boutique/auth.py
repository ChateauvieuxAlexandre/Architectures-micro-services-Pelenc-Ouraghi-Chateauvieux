"""Authentification JWT partagée par les services Voxenfer.
Implémentation de la vérification du jeton (TP 09).
"""
import os
from functools import wraps
import jwt          # PyJWT : jwt.encode / jwt.decode (HS256)
from flask import request, jsonify

SECRET = os.environ.get("JWT_SECRET", "je-suis-le-secret-tres-secret-12")
def require_jwt(f):
    """Décorateur : refuse la requête (401) si le jeton est absent ou invalide ;
    sinon pose le payload dans request.joueur et exécute la route.
    """
    @wraps(f)
    def verifie(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"erreur": "Jeton manquant ou mal formaté"}), 401
        
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET, algorithms=["HS256"])
            request.joueur = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"erreur": "Jeton expiré"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"erreur": "Jeton invalide"}), 401
            
        return f(*args, **kwargs)
    return verifie
def require_role(role):
    """Décorateur paramétré : comme require_jwt, mais exige en plus que `role`
    figure dans la liste des rôles du jeton (sinon 403).
    """
    def decorateur(f):
        @wraps(f)
        def verifie(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"erreur": "Jeton manquant ou mal formaté"}), 401
            
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, SECRET, algorithms=["HS256"])
                request.joueur = payload
            except jwt.ExpiredSignatureError:
                return jsonify({"erreur": "Jeton expiré"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"erreur": "Jeton invalide"}), 401
                
            if "roles" not in request.joueur or role not in request.joueur["roles"]:
                return jsonify({"erreur": f"Accès refusé. Rôle '{role}' requis."}), 403
                
            return f(*args, **kwargs)
        return verifie
    return decorateur