# Starter Voxenfer

Point de départ minimal pour le projet. Tout ce qu'il contient, vous l'avez vu aux TP 08 à 12.

## Contenu

```
starter/
├── service-template/      ← à COPIER pour créer votre service
│   ├── app.py             ← Flask : /health, /metrics (charpente ; vos routes à écrire)
│   ├── db.py              ← base SQLite via ORM SQLAlchemy (vos modèles à écrire)
│   ├── auth.py            ← JWT : charpente require_jwt/require_role À COMPLÉTER
│   ├── requirements.txt
│   └── Dockerfile
├── luanti-db/init.sql     ← Postgres au schéma Luanti (stand-in du serveur de jeu)
├── Caddyfile              ← gateway : SQUELETTE à compléter (modèle commenté, le reste à vous) - G1
├── docker-compose.yml     ← orchestration : SQUELETTE à compléter (modèle commenté, le reste à vous) - G1
└── mod-voxenfer/          ← mod Luanti FOURNI, non noté (pont temps réel jeu <-> services)
```

> **`service-monde`** (lecteur de la base Luanti) est un **livrable G1** : à coder dans `service-monde/`. Son bloc est le seul déjà actif dans le `docker-compose.yml` (relié à `luanti-db`). Spécifié dans `2-contrats.md`.

> **Le `Caddyfile` et le `docker-compose.yml` sont des SQUELETTES** : aucun service métier n'y est actif, juste un **modèle commenté** à recopier. C'est à **G1** d'écrire les blocs de tous les services (routage dans `2-contrats.md`).

> **`mod-voxenfer/` est illustratif et non noté** : il relie le jeu à vos services dans les **deux sens** (le jeu appelle vos services sur événement ; vos décisions sont exécutées en jeu via les **files d'actions**). C'est du Lua, **géré côté enseignant** : vous n'y touchez pas. Voir son `README.md`.

## Pour un groupe service (G2-G7)

1. Copiez `service-template/` en `service-<votre-domaine>/` (ex. `service-comptes/`).
2. Écrivez vos routes dans `app.py` (la charpente `/health` + `/metrics` est là ; voir `2-contrats.md` pour les routes attendues de votre service).
3. Définissez vos tables dans `db.py` (vos classes-modèles SQLAlchemy).
4. Complétez `auth.py` (vérification du jeton, cf. `2-contrats.md` et TP 09) ; gardez `/health` et `/metrics` tels quels.
5. Testez en local : `pip install -r requirements.txt` puis `python app.py` (le service écoute sur `5000`).

## Pour le groupe plateforme (G1)

1. Récupérez les dossiers `service-*/` des 6 groupes.
2. Codez `service-monde` (lecteur **lecture seule** de la base Luanti `luanti-db`) : routes `/joueurs`, `/positions/<pseudo>`... (voir `2-contrats.md`).
3. Écrivez le `Caddyfile` : un bloc `handle_path` par service, dont `/monde` (un modèle commenté est fourni ; table de routage dans `2-contrats.md`).
4. Complétez le `docker-compose.yml` : un bloc + un volume par service, **même** `JWT_SECRET` (un modèle de service commenté est fourni ; `luanti-db` et le serveur de jeu sont déjà là).
5. `docker compose up --build` : tout doit démarrer.
6. La gateway est sur `http://localhost:8080`. Testez : `curl http://localhost:8080/comptes/health` et `curl http://localhost:8080/monde/joueurs`.

> **Astuce : démarrer avant que tout soit prêt.** `./demarrer.sh` ne lance que les services **déclarés dans le compose dont le dossier existe** (toujours la gateway + `luanti-db`) ; la gateway renvoie simplement 502 pour les absents. Idéal pour tester la plateforme (`curl .../monde/health`) sans attendre les 6 services. Quand tout est là, `docker compose up --build` lance l'ensemble.

*Bonus G1* : une **carte web des positions** des joueurs, lue depuis `service-monde`.

*Avec le jeu (optionnel)* : **`./jouer.sh`** (= `./demarrer.sh --jeu`) clone Minetest Game et démarre les services présents avec un **vrai serveur Luanti** (profile `jeu`, `auth`/`player` en PostgreSQL sur `luanti-db`). Le mod appelle alors vos services. Pour voir des données réelles, connectez un **client Luanti** sur `127.0.0.1:30000` (serveur headless : rien ne remonte sans client).

## Rappels

- **Lectures ouvertes, écritures protégées** (`@require_jwt`).
- Le `JWT_SECRET` est **le même pour tous** (fixé dans `docker-compose.yml`).
- Un service joint un autre par son **nom** (`http://service-economie:5000`), jamais par `localhost`.
