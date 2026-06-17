# Voxenfer — Groupe G1 Plateforme

## Objectif

Ce projet correspond à la partie G1 - Plateforme du projet Voxenfer.

Le rôle du groupe G1 est de mettre en place l’infrastructure commune :

la gateway HTTP avec Caddy ;
l’orchestration des services avec Docker Compose ;
la base PostgreSQL de Luanti ;
le service service-monde, qui lit l’état sauvegardé du serveur Luanti ;
l’intégration des services des autres groupes.

La gateway est le seul point d’entrée HTTP exposé sur la machine. Elle écoute sur :

http://localhost:8080

Le serveur de jeu Luanti, lorsqu’il est lancé, écoute sur :

127.0.0.1:30000

## Services principaux

| Service | Rôle |
| --- | --- |
| `gateway` | Reverse proxy Caddy, expose le port `8080` |
| `luanti-db` | Base PostgreSQL du serveur Luanti |
| `service-monde` | API Flask qui lit la base Luanti en lecture seule |
| `service-comptes` | Gestion des comptes et JWT |
| `service-economie` | Gestion des pièces |
| `service-boutique` | Catalogue et achats |
| `service-classements` | Scores et classement |
| `service-moderation` | Signalements et bans |
| `service-evenements` | Événements et téléportations |
| `luanti` | Serveur de jeu Luanti, lancé uniquement avec le profil `jeu` |


Exemples via la gateway :

curl http://localhost:8080/monde/joueurs

curl http://localhost:8080/monde/positions/alex

curl http://localhost:8080/monde/joueurs/alex/inventaire

## Commandes utiles

Voir les conteneurs lancés :

docker compose ps

Voir les logs :

docker compose logs -f

Voir les logs de service-monde :

docker compose logs -f service-monde

Arrêter les services :

docker compose down

## Liens

Lien docs partager : https://docs.google.com/document/d/1JJmtMBlpT2KCPqm6c5Ha70bV9Vo7kvma7hRV8ct41mY/edit?usp=sharing
Lien docs journal : https://docs.google.com/document/d/1X84qFh_DYggyUsCKdpohlPH7XCGywfTaqhoJ7BpIU7g/edit?usp=sharing
Lien Github : https://github.com/ChateauvieuxAlexandre/Architectures-micro-services-Pelenc-Ouraghi-Chateauvieux