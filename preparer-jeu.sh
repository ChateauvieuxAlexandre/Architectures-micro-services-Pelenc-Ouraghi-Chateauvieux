#!/usr/bin/env bash
# Auteur : Philippe ROUSSILLE <roussille@3il.fr>
# Prépare minetest_game.zip -- À LANCER UNE FOIS sur une machine AVEC Internet.
#
# Les postes (pare-feu) ne pourront pas télécharger le jeu : il suffit alors de
# leur fournir le minetest_game.zip produit ici (Moodle / clé USB), à poser à côté
# de demarrer.sh / jouer.sh. Le lanceur l'extraira, sans aucun accès réseau au jeu.
set -euo pipefail
cd "$(dirname "$0")"

rm -rf minetest_game minetest_game.zip
echo "==> Clonage de Minetest Game (Internet requis)..."
git clone --depth 1 https://github.com/minetest/minetest_game minetest_game
rm -rf minetest_game/.git
echo "==> Compression en minetest_game.zip..."
zip -rq minetest_game.zip minetest_game
rm -rf minetest_game
echo "OK : minetest_game.zip prêt ($(du -h minetest_game.zip | cut -f1)). À distribuer aux postes."
