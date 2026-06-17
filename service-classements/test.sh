#!/usr/bin/env bash
# Script de test bout-en-bout pour service-classements (G5), via la gateway.
#
# Lance les commandes curl du contrat (2-contrats.md / README.md) et vérifie
# les codes HTTP attendus. Pense à démarrer la stack avant :
#   docker compose up --build -d
#
# Usage : ./test.sh [URL_BASE]
#   URL_BASE par défaut : http://localhost:8080 (via la gateway)

set -uo pipefail

BASE="${1:-http://localhost:8080}"
JWT_SECRET="${JWT_SECRET:-je-suis-le-secret-tres-secret-12}"

ECHECS=0
TOTAL=0

b64url() {
	openssl base64 -A | tr '+/' '-_' | tr -d '='
}

faire_jwt() {
	# faire_jwt '{"pseudo":"maxime","roles":["joueur"]}'
	local payload="$1"
	local header='{"alg":"HS256","typ":"JWT"}'
	local h b sig
	h=$(printf '%s' "$header" | b64url)
	b=$(printf '%s' "$payload" | b64url)
	sig=$(printf '%s.%s' "$h" "$b" | openssl dgst -sha256 -hmac "$JWT_SECRET" -binary | b64url)
	printf '%s.%s.%s' "$h" "$b" "$sig"
}

verifier() {
	# verifier "description" code_attendu code_obtenu
	local desc="$1" attendu="$2" obtenu="$3"
	TOTAL=$((TOTAL + 1))
	if [ "$attendu" = "$obtenu" ]; then
		echo "  OK   $desc (HTTP $obtenu)"
	else
		echo "  FAIL $desc (attendu $attendu, obtenu $obtenu)"
		ECHECS=$((ECHECS + 1))
	fi
}

requete() {
	# requete METHODE PATH [JSON] [TOKEN] -> écrit le corps sur stdout, le code sur stderr (via fd 3)
	local methode="$1" chemin="$2" corps="${3:-}" jeton="${4:-}"
	local args=(-s -o /tmp/g5_test_body -w '%{http_code}' -X "$methode" "$BASE$chemin")
	[ -n "$corps" ] && args+=(-H "Content-Type: application/json" -d "$corps")
	[ -n "$jeton" ] && args+=(-H "Authorization: Bearer $jeton")
	curl "${args[@]}"
}

afficher_corps() {
	if command -v jq >/dev/null 2>&1; then
		jq -c . /tmp/g5_test_body 2>/dev/null || cat /tmp/g5_test_body
	else
		cat /tmp/g5_test_body
	fi
	echo
}

echo "=== Tests service-classements (base: $BASE) ==="
echo

TOKEN=$(faire_jwt '{"pseudo":"maxime","roles":["joueur"]}')

echo "--- /health ---"
code=$(requete GET /classements/health)
afficher_corps
verifier "GET /classements/health -> 200" 200 "$code"
echo

echo "--- POST /scores sans jeton -> 401 ---"
code=$(requete POST /classements/scores '{"pseudo":"maxime","points":10}')
afficher_corps
verifier "POST /classements/scores sans jeton -> 401" 401 "$code"
echo

echo "--- POST /scores avec points négatif -> 400 ---"
code=$(requete POST /classements/scores '{"pseudo":"maxime","points":-5}' "$TOKEN")
afficher_corps
verifier "POST /classements/scores points négatif -> 400" 400 "$code"
echo

echo "--- POST /scores avec points non entier -> 400 ---"
code=$(requete POST /classements/scores '{"pseudo":"maxime","points":"dix"}' "$TOKEN")
afficher_corps
verifier "POST /classements/scores points non entier -> 400" 400 "$code"
echo

echo "--- POST /scores valide (10 points) -> 201 ---"
code=$(requete POST /classements/scores '{"pseudo":"maxime","points":10}' "$TOKEN")
afficher_corps
verifier "POST /classements/scores valide -> 201" 201 "$code"
echo

echo "--- POST /scores rejoué (+10) -> cumule à 20 ---"
code=$(requete POST /classements/scores '{"pseudo":"maxime","points":10}' "$TOKEN")
points=$(command -v jq >/dev/null 2>&1 && jq -r '.points' /tmp/g5_test_body || grep -o '"points":[0-9]*' /tmp/g5_test_body | grep -o '[0-9]*')
afficher_corps
verifier "POST /scores rejoué -> 201" 201 "$code"
verifier "POST /scores rejoué -> points cumulés à 20" 20 "$points"
echo

echo "--- GET /scores/maxime -> 200 ---"
code=$(requete GET /classements/scores/maxime)
afficher_corps
verifier "GET /classements/scores/maxime -> 200" 200 "$code"
echo

echo "--- GET /scores/inconnu -> 404 ---"
code=$(requete GET /classements/scores/inconnu)
afficher_corps
verifier "GET /classements/scores/inconnu -> 404" 404 "$code"
echo

echo "--- GET /classement (trié décroissant) ---"
code=$(requete GET /classements/classement)
afficher_corps
verifier "GET /classements/classement -> 200" 200 "$code"
echo

echo "--- GET /classement/top/1 ---"
code=$(requete GET /classements/classement/top/1)
afficher_corps
verifier "GET /classements/classement/top/1 -> 200" 200 "$code"
echo

echo "--- GET /classement?page=1&taille=1 (bonus pagination) ---"
code=$(requete GET "/classements/classement?page=1&taille=1")
afficher_corps
verifier "GET /classements/classement paginé -> 200" 200 "$code"
echo

echo "--- GET /classement/periode/jour (bonus) ---"
code=$(requete GET /classements/classement/periode/jour)
afficher_corps
verifier "GET /classements/classement/periode/jour -> 200" 200 "$code"
echo

echo "--- GET /classement/periode/mois (invalide) -> 400 ---"
code=$(requete GET /classements/classement/periode/mois)
afficher_corps
verifier "GET /classements/classement/periode/mois -> 400" 400 "$code"
echo

echo "--- GET /badges/maxime (bonus) -> 200 ---"
code=$(requete GET /classements/badges/maxime)
afficher_corps
verifier "GET /classements/badges/maxime -> 200" 200 "$code"
echo

echo "--- GET /badges/inconnu -> 404 ---"
code=$(requete GET /classements/badges/inconnu)
afficher_corps
verifier "GET /classements/badges/inconnu -> 404" 404 "$code"
echo

rm -f /tmp/g5_test_body

echo "=== Résultat : $((TOTAL - ECHECS))/$TOTAL tests OK ==="
if [ "$ECHECS" -gt 0 ]; then
	echo "=== $ECHECS échec(s) ==="
	exit 1
fi
exit 0
