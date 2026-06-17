# Mod Voxenfer : le pont jeu <-> services

**Fourni, illustratif, NON noté. Vous n'avez rien à coder ni à rendre ici.**

Ce petit mod Luanti existe pour **rendre concret** votre micro-service : il relie le jeu à vos **services** par des appels **HTTP via la gateway**, comme le ferait un vrai serveur, et **dans les deux sens** : le jeu appelle vos services (sur événement), **et** vos services font agir le jeu (via les files d'actions).

C'est la réponse à la question « *à quoi sert mon service, déjà ?* » : votre service-classements existe parce que **quand un joueur meurt, le jeu lui envoie un score**.

## Sens 1 : le jeu appelle vos services (sur événement)

| Événement en jeu | Service appelé | Appel (via la gateway) |
|---|---|---|
| Connexion d'un joueur | comptes | `GET /comptes/joueurs/<pseudo>` (accueil + rôles) |
| Connexion d'un joueur | moderation | `GET /moderation/bannis/<pseudo>` → **expulse** si banni |
| Connexion d'un joueur | evenements | `GET /evenements` (annonce le prochain) |
| Mort d'un joueur | classements | `POST /classements/scores` (le tueur marque) |
| Commande `/acheter <id>` | boutique | `POST /boutique/acheter` (qui débite l'économie) |
| Commande `/solde` | economie | `GET /economie/solde/<pseudo>` |
| Commande `/signaler <joueur> <raison>` | moderation | `POST /moderation/signalements` |

Le mod est un **bon voisin HTTP** (cf. TP 10) : si un service répond mal ou est injoignable, il **journalise et continue** : il ne fait jamais planter le jeu.

## Sens 2 : vos services agissent dans le jeu (files d'actions)

Un mod ne peut faire que des appels **sortants**. Pour que « le service décide -> le jeu agit », le mod **interroge** régulièrement (sur `globalstep`) les **files d'actions** des services, **exécute** en jeu, puis **acquitte** (cf. `2-contrats.md`) :

| File lue par le mod | Effet en jeu |
|---|---|
| `GET /boutique/livraisons` | l'objet acheté apparaît dans l'inventaire |
| `GET /evenements/teleportations` | les inscrits sont téléportés à l'arène |
| `GET /moderation/actions` | confisquer / donner un objet, spawn de loot |
| `GET /moderation/bannis` (réconciliation) | les bannis connectés sont expulsés |

Plus des **reflets d'état** (simple lecture, sans file) : solde en HUD, top du classement, privilèges selon le rôle. Côté services, **tout reste du HTTP**.

## Pour l'essayer (facultatif)

Vous n'êtes **pas** obligés de lancer Luanti : votre service se valide au `curl` et dans le `docker compose`. Mais si vous voulez voir le pont vivre :

1. Lancez l'écosystème : `docker compose up --build` (gateway sur `:8080`).
2. Copiez ce dossier `mod-voxenfer/` dans les **mods** de votre monde Luanti et activez le mod.
3. Dans `minetest.conf`, autorisez l'accès HTTP et pointez la gateway :

   ```
   secure.http_mods = voxenfer
   voxenfer.gateway_url = http://localhost:8080
   voxenfer.server_token = <un JWT admin émis par service-comptes>
   ```

> Le jeton sert aux **écritures** (poster un score, un signalement). En vrai, chaque joueur se connecterait via `service-comptes` et utiliserait **son** jeton ; ici le serveur en porte un seul, pour garder l'exemple court.

4. Connectez-vous, tapez `/solde`, mourez, `/acheter 1`... et regardez les appels arriver sur vos services (`docker compose logs -f`).

## À retenir

- Ce mod ne fait que **consommer votre API** : tout ce qui compte côté note, c'est que **vos routes** (cf. `2-contrats.md`) répondent juste, avec les bons codes.
- `core` est le nom actuel de l'API Luanti ; `minetest` (utilisé ici) en reste un alias fonctionnel.
