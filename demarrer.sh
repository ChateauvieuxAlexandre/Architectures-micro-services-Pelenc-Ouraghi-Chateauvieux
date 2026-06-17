#!/usr/bin/env bash
# Auteur : Philippe ROUSSILLE <roussille@3il.fr>
# Démarre l'écosystème Voxenfer en ne lançant QUE ce qui est prêt :
#
#  - toujours : la gateway + la base Luanti (luanti-db)
#  - + chaque service DÉCLARÉ dans docker-compose.yml dont le dossier existe
#    (G1 déclare les services au fur et à mesure qu'il les ajoute)
#  - avec --jeu : récupère Minetest Game et ajoute le serveur de jeu Luanti
#
# Utile pour tester la plateforme AVANT que tous les services soient prêts : la
# gateway renvoie juste 502 pour un service absent, mais le reste tourne. Quand
# tout est en place, un simple `docker compose up --build` lance l'ensemble.

set -euo pipefail
cd "$(dirname "$0")"

JEU=0
[ "${1:-}" = "--jeu" ] && JEU=1

A_LANCER="gateway luanti-db"
ABSENTS=""
# Services métier déclarés dans le compose (G1 en ajoute un bloc par service).
for s in $(grep -oE '^  service-[a-z-]+:' docker-compose.yml | tr -d ' :'); do
	if [ -f "$s/Dockerfile" ]; then
		A_LANCER="$A_LANCER $s"
	else
		ABSENTS="$ABSENTS $s"
	fi
done

PROFILE=""
if [ "$JEU" = "1" ]; then
	if [ ! -d minetest_game ]; then
		if [ -f minetest_game.zip ]; then
			echo "==> Extraction de minetest_game.zip (hors ligne)..."
			unzip -q minetest_game.zip
		else
			echo "==> Pas de zip : clonage depuis GitHub (non bloqué par le pare-feu)..."
			git clone --depth 1 https://github.com/minetest/minetest_game minetest_game
		fi
	fi
	PROFILE="--profile jeu"
	A_LANCER="$A_LANCER luanti"
fi

echo "==> On lance :$A_LANCER"
[ -n "$ABSENTS" ] && echo "==> Ignorés (déclarés mais dossier absent, 502 via la gateway) :$ABSENTS"

# shellcheck disable=SC2086
docker compose $PROFILE up --build $A_LANCER

echo
echo "Gateway : http://localhost:8080   (ex. curl http://localhost:8080/monde/health)"
[ "$JEU" = "1" ] && echo "Serveur de jeu : UDP 30000 (client Luanti -> 127.0.0.1:30000)"
echo "Tout arrêter : docker compose --profile jeu down -v"
