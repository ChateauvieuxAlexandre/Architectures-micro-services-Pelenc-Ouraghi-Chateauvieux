-- =====================================================================
-- Voxenfer : pont entre le jeu Luanti et l'écosystème de micro-services
-- =====================================================================
-- Auteur : Philippe ROUSSILLE <roussille@3il.fr>
-- Mod FOURNI, ILLUSTRATIF, NON NOTÉ. Vous n'avez pas à le toucher.
--
-- Il fait le pont DANS LES DEUX SENS, par HTTP à travers la gateway, comme un
-- vrai jeu le ferait. Il montre POURQUOI chaque service existe.
--
-- SENS 1 - le jeu appelle les services (sur événement) :
--   connexion d'un joueur  -> service-comptes (qui es-tu ?)
--                          -> service-moderation (banni ? -> expulsion)
--                          -> service-evenements (prochain événement)
--   mort d'un joueur       -> service-classements (marquer des points)
--   /acheter <id>          -> service-boutique (qui débite service-economie)
--   /solde                 -> service-economie
--   /signaler <j> <raison> -> service-moderation
--
-- SENS 2 - les services agissent dans le jeu : le mod INTERROGE leurs files
-- d'actions (sur globalstep), exécute en jeu, puis acquitte (cf. 2-contrats.md) :
--   boutique /livraisons          -> livrer un objet dans l'inventaire
--   evenements /teleportations    -> téléporter les inscrits à l'arène
--   moderation /actions + /bannis -> confisquer/donner, expulser
--
-- (« minetest » est l'ancien nom de l'API ; « core » est le nom actuel de
--  Luanti : les deux fonctionnent. On garde « minetest », plus répandu.)

-- --- Accès HTTP (doit être demandé au chargement, pas dans un callback) ----
local http = minetest.request_http_api()
if not http then
	minetest.log("warning", "[voxenfer] HTTP non autorisé. Ajoutez dans "
		.. "minetest.conf : secure.http_mods = voxenfer")
	return
end

-- --- Configuration (minetest.conf) ----------------------------------------
local GATEWAY = minetest.settings:get("voxenfer.gateway_url")
	or "http://localhost:8080"
-- En vrai, chaque joueur se connecterait via service-comptes (/login) et
-- utiliserait SON jeton. Ici, le serveur porte un seul jeton (admin) pour
-- garder l'illustration courte : on le pose dans minetest.conf.
local TOKEN = minetest.settings:get("voxenfer.server_token") or ""

-- --- Petits aides HTTP -----------------------------------------------------
local function headers()
	return {
		"Authorization: Bearer " .. TOKEN,
		"Content-Type: application/json",
	}
end

-- Écriture (POST) : on est « bon voisin HTTP » ; si le service répond mal ou
-- est injoignable, on NE bloque PAS le jeu, on journalise et on continue.
local function post(service, chemin, corps, on_ok)
	http.fetch({
		url = GATEWAY .. "/" .. service .. chemin,
		method = "POST",
		extra_headers = headers(),
		data = corps and minetest.write_json(corps) or "{}",
		timeout = 5,
	}, function(res)
		if res.succeeded and res.code < 300 then
			if on_ok then on_ok(res) end
		else
			minetest.log("action", "[voxenfer] " .. service .. chemin
				.. " -> code " .. tostring(res.code))
		end
	end)
end

-- Lecture (GET) : on envoie quand même le jeton (les files d'actions sont
-- protégées ; pour les routes ouvertes, l'en-tête est juste ignoré).
local function get(service, chemin, on_ok)
	http.fetch({
		url = GATEWAY .. "/" .. service .. chemin,
		extra_headers = headers(),
		timeout = 5,
	}, function(res)
		if res.succeeded and res.code == 200 and on_ok then
			on_ok(minetest.parse_json(res.data) or {})
		end
	end)
end

-- Professions (bonus comptes) : effet en jeu reflété depuis service-comptes.
-- physique (set_physics_override) + privilège + titre affiché en HUD.
local professions = {
	mineur    = { titre = "Mineur",    physics = { speed = 1.5 },             priv = "fast" },
	batisseur = { titre = "Batisseur", physics = {},                          priv = "fly" },
	guerrier  = { titre = "Guerrier",  physics = { jump = 1.3, speed = 1.2 } },
}

-- =====================================================================
-- CONNEXION  ->  comptes + moderation + evenements
-- =====================================================================
minetest.register_on_joinplayer(function(player)
	local pseudo = player:get_player_name()

	-- service-moderation : ce joueur est-il banni ? Si oui, on l'expulse.
	get("moderation", "/bannis/" .. pseudo, function(data)
		if data.banni then
			minetest.kick_player(pseudo, "Vous êtes banni du serveur Voxenfer.")
		end
	end)

	-- service-comptes : qui est ce joueur (rôles) ? On l'accueille, et on PROJETTE
	-- ses rôles en privilèges Luanti (reflet d'état : pas de file, juste une lecture).
	get("comptes", "/joueurs/" .. pseudo, function(data)
		local roles = data.roles or { "joueur" }
		minetest.chat_send_player(pseudo,
			"Bienvenue ! Rôle(s) : " .. table.concat(roles, ", "))
		local est = {}
		for _, r in ipairs(roles) do est[r] = true end
		local privs = minetest.get_player_privs(pseudo)
		privs.kick = (est.moderateur or est.admin) or nil
		privs.ban = est.admin or nil

		-- profession (bonus) : physique + privilège + titre affiché en HUD
		local prof = professions[data.profession or ""]
		if prof then
			local j = minetest.get_player_by_name(pseudo)
			if j then
				if next(prof.physics) then j:set_physics_override(prof.physics) end
				j:hud_add({
					hud_elem_type = "text", position = { x = 0.5, y = 0.08 },
					text = "Profession : " .. prof.titre, number = 0xFFD700,
					alignment = { x = 0, y = 0 }, scale = { x = 100, y = 24 },
				})
			end
			if prof.priv then privs[prof.priv] = true end
		end
		minetest.set_player_privs(pseudo, privs)
	end)

	-- service-evenements : annoncer le prochain événement, s'il y en a un.
	-- (la collection est à la racine du service : "/" -> gateway /evenements/)
	get("evenements", "/", function(liste)
		if liste[1] and liste[1].nom then
			minetest.chat_send_player(pseudo,
				"Prochain événement : " .. liste[1].nom)
		end
	end)
end)

-- =====================================================================
-- MORT  ->  classements
-- =====================================================================
minetest.register_on_dieplayer(function(player, reason)
	local victime = player:get_player_name()
	-- En PvP, c'est le TUEUR qui marque ; sinon on crédite quand même la
	-- victime (mort « héroïque ») pour que l'exemple produise un score.
	local marqueur = victime
	if reason and reason.type == "punch" and reason.object
		and reason.object:is_player() then
		marqueur = reason.object:get_player_name()
	end
	post("classements", "/scores", { pseudo = marqueur, points = 10 })
end)

-- =====================================================================
-- ACHAT  ->  boutique  (qui débite economie)
-- =====================================================================
minetest.register_chatcommand("acheter", {
	params = "<objet_id>",
	description = "Acheter un objet de la boutique Voxenfer",
	func = function(pseudo, param)
		local id = tonumber(param)
		if not id then
			return false, "Usage : /acheter <objet_id>"
		end
		post("boutique", "/acheter", { objet_id = id }, function()
			minetest.chat_send_player(pseudo, "Achat effectué !")
		end)
		return true, "Achat en cours..."
	end,
})

-- =====================================================================
-- SOLDE  ->  economie  (lecture)
-- =====================================================================
minetest.register_chatcommand("solde", {
	description = "Voir son solde de pièces Voxenfer",
	func = function(pseudo)
		get("economie", "/solde/" .. pseudo, function(data)
			minetest.chat_send_player(pseudo,
				"Solde : " .. tostring(data.pieces or 0) .. " pièces")
		end)
		return true
	end,
})

-- =====================================================================
-- SIGNALEMENT  ->  moderation
-- =====================================================================
minetest.register_chatcommand("signaler", {
	params = "<joueur> <raison>",
	description = "Signaler un joueur aux modérateurs",
	func = function(pseudo, param)
		local vise, raison = param:match("^(%S+)%s+(.+)$")
		if not vise then
			return false, "Usage : /signaler <joueur> <raison>"
		end
		post("moderation", "/signalements",
			{ pseudo_vise = vise, raison = raison })
		return true, "Signalement envoyé aux modérateurs."
	end,
})

-- =====================================================================
-- SENS 2 : les services agissent dans le jeu (files d'actions)
-- =====================================================================
-- Un mod ne reçoit rien : c'est LUI qui interroge les files des services (sur
-- globalstep), exécute en jeu, puis ACQUITTE. Voir 2-contrats.md.

-- type d'action (champ JSON) -> fonction Lua qui l'exécute en jeu.
-- Retourne true si c'est fait (on acquitte), false si à réessayer (cible absente).
local executer = {}

executer["livrer_objet"] = function(a)
	local j = minetest.get_player_by_name(a.cible)
	if not j then return false end                 -- hors ligne : on réessaiera
	j:get_inventory():add_item("main", ItemStack(a.objet))
	minetest.chat_send_player(a.cible, "Livraison Voxenfer : " .. a.objet)
	return true
end
executer["donner_objet"] = executer["livrer_objet"]

executer["confisquer"] = function(a)
	local j = minetest.get_player_by_name(a.cible)
	if not j then return false end
	j:get_inventory():remove_item("main", ItemStack(a.objet))
	minetest.chat_send_player(a.cible, "Objet confisqué : " .. a.objet)
	return true
end

executer["teleporter"] = function(a)
	local j = minetest.get_player_by_name(a.cible)
	if not j then return false end
	j:set_pos({ x = a.x, y = a.y, z = a.z })
	return true
end

executer["spawn_item"] = function(a)
	minetest.add_item({ x = a.x, y = a.y, z = a.z }, a.objet)   -- au sol : toujours faisable
	return true
end

-- Vide une file : GET en attente -> exécute -> POST ack (seulement si réussi).
local function vider_file(service, chemin)
	get(service, chemin, function(actions)
		for _, a in ipairs(actions or {}) do
			local fn = executer[a.type]
			if fn and fn(a) then
				post(service, chemin .. "/" .. a.id .. "/fait", {})
			end
		end
	end)
end

-- Bans : réconciliation idempotente (pas de file) : on relit et on expulse.
local function appliquer_bans()
	get("moderation", "/bannis", function(liste)
		for _, b in ipairs(liste or {}) do
			if minetest.get_player_by_name(b.pseudo) then
				minetest.kick_player(b.pseudo, "Vous êtes banni du serveur Voxenfer.")
			end
		end
	end)
end

local INTERVALLE = 5          -- files d'actions
local INTERVALLE_POS = 2      -- positions live (anime la carte du tableau de bord)
local horloge, horloge_pos = 0, 0
minetest.register_globalstep(function(dtime)
	-- Positions LIVE : on pousse la position de chaque joueur connecté vers
	-- service-presence (qui la garde en mémoire). Un déconnecté cesse d'être
	-- poussé -> il expire côté service.
	horloge_pos = horloge_pos + dtime
	if horloge_pos >= INTERVALLE_POS then
		horloge_pos = 0
		for _, j in ipairs(minetest.get_connected_players()) do
			local p = j:get_pos()
			post("presence", "/" .. j:get_player_name(),
				{ x = p.x, y = p.y, z = p.z, hp = j:get_hp() })
		end
	end
	-- Files d'actions (cadence plus lente).
	horloge = horloge + dtime
	if horloge < INTERVALLE then return end
	horloge = 0
	appliquer_bans()
	vider_file("boutique", "/livraisons")
	vider_file("evenements", "/teleportations")
	vider_file("moderation", "/actions")
end)

minetest.log("action", "[voxenfer] pont bidirectionnel chargé (gateway : "
	.. GATEWAY .. ")")
