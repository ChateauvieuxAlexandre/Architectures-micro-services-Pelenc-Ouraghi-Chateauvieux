import jwt
import datetime
from app import app
from auth import SECRET
def tester_auth():
    print("=== Début des tests de l'authentification ===")
    
    # On crée un faux client web pour tester notre application sans avoir besoin de l'allumer
    client = app.test_client()
    # 1. Création de faux jetons pour nos tests
    # Jeton Joueur normal
    token_joueur = jwt.encode(
        {"pseudo": "maxime", "roles": ["joueur"]},
        SECRET,
        algorithm="HS256"
    )
    # Jeton Admin
    token_admin = jwt.encode(
        {"pseudo": "super_gilbert", "roles": ["joueur", "admin"]},
        SECRET,
        algorithm="HS256"
    )
    # Jeton Expiré (créé il y a 10 jours)
    token_expire = jwt.encode(
        {
            "pseudo": "vieux_joueur", 
            "roles": ["joueur"],
            "exp": datetime.datetime.utcnow() - datetime.timedelta(days=10)
        },
        SECRET,
        algorithm="HS256"
    )
    # --- TEST A : Essayer d'acheter (nécessite juste d'être connecté, @require_jwt) ---
    print("\n[TEST A] Route /acheter (Nécessite juste un token valide)")
    
    # Sans token
    rep = client.post("/acheter", json={"objet_id": 1})
    print(f"Sans token -> Status {rep.status_code} | {rep.get_json()}")
    
    # Avec un token expiré
    rep = client.post("/acheter", json={"objet_id": 1}, headers={"Authorization": f"Bearer {token_expire}"})
    print(f"Token expiré -> Status {rep.status_code} | {rep.get_json()}")
    # Avec un faux token trafiqué
    rep = client.post("/acheter", json={"objet_id": 1}, headers={"Authorization": "Bearer blabla.trafiqué.123"})
    print(f"Token trafiqué -> Status {rep.status_code} | {rep.get_json()}")
    
    # Avec un token valide (joueur normal)
    # L'achat va essayer d'appeler l'économie (qui n'est pas allumée) donc ça devrait faire un 503
    rep = client.post("/acheter", json={"objet_id": 1}, headers={"Authorization": f"Bearer {token_joueur}"})
    print(f"Token valide -> Status {rep.status_code} | {rep.get_json()} (Le 503 est normal car le service economie est éteint)")
    # --- TEST B : Créer un objet dans le catalogue (nécessite le rôle 'admin', @require_role) ---
    print("\n[TEST B] Route /objets POST (Nécessite le rôle 'admin')")
    
    payload_objet = {"nom": "Test", "prix": 10, "item": "default:test"}
    
    # Joueur normal essaie de créer (devrait être refusé avec 403)
    rep = client.post("/objets", json=payload_objet, headers={"Authorization": f"Bearer {token_joueur}"})
    print(f"Joueur normal -> Status {rep.status_code} | {rep.get_json()}")
    
    # Admin essaie de créer (devrait être accepté avec 201)
    rep = client.post("/objets", json=payload_objet, headers={"Authorization": f"Bearer {token_admin}"})
    print(f"Admin -> Status {rep.status_code} | {rep.get_json()}")
if __name__ == "__main__":
    tester_auth()
