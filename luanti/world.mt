# Backends du monde Voxenfer.
# Auteur : Philippe ROUSSILLE <roussille@3il.fr>
#
# IMPORTANT : les backends se fixent à la CRÉATION du monde et ne se changent plus
# après coup. auth + player en PostgreSQL pour que service-monde lise EXACTEMENT
# les mêmes données que le serveur écrit. La map reste en sqlite3 (locale).
#
# gameid : aucun jeu n'est embarqué dans l'image ; jouer.sh récupère Minetest Game.
gameid = minetest_game

backend = sqlite3
player_backend = postgresql
auth_backend = postgresql
mod_storage_backend = sqlite3

load_mod_voxenfer = true

pgsql_player_connection = host=luanti-db port=5432 user=luanti password=luanti dbname=luanti
pgsql_auth_connection = host=luanti-db port=5432 user=luanti password=luanti dbname=luanti
