#!/usr/bin/env bash
# Auteur : Philippe ROUSSILLE <roussille@3il.fr>
# Raccourci : démarre l'écosystème disponible AVEC le serveur de jeu Luanti.
# (Équivaut à `./demarrer.sh --jeu` : ne lance que les services présents + le jeu.)
exec "$(dirname "$0")/demarrer.sh" --jeu "$@"
