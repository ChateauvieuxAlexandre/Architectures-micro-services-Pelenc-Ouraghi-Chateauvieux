-- Schéma PostgreSQL d'un serveur Luanti (backends auth + player), reproduit à
-- l'identique depuis le moteur (src/database/database-postgresql.cpp).
-- Auteur : Philippe ROUSSILLE <roussille@3il.fr>
--
-- Ce conteneur Postgres TIENT LIEU de la base d'un vrai serveur Luanti qui aurait
-- été configuré en PostgreSQL (minetest.conf : auth_backend = postgresql,
-- player_backend = postgresql). On n'a pas besoin de lancer Luanti pour la démo :
-- service-monde lit ces tables EN LECTURE SEULE et les expose en HTTP/JSON.
--
-- IMPORTANT : service-monde ne possède PAS ce schéma (c'est celui de Luanti). Il
-- s'y ADAPTE (pattern adaptateur / anti-corruption layer) : les autres services
-- ne touchent jamais cette base, ils passent par l'API HTTP de service-monde.

-- ============================ Backend AUTH ============================
CREATE TABLE auth (
    id SERIAL,
    name TEXT UNIQUE,
    password TEXT,
    last_login INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id)
);

CREATE TABLE user_privileges (
    id INT,
    privilege TEXT,
    PRIMARY KEY (id, privilege),
    CONSTRAINT fk_id FOREIGN KEY (id) REFERENCES auth (id) ON DELETE CASCADE
);

-- ============================ Backend PLAYER ==========================
-- (Luanti crée posX/posY/posZ sans guillemets : Postgres les range en minuscules.)
CREATE TABLE player (
    name VARCHAR(60) NOT NULL,
    pitch NUMERIC(15, 7) NOT NULL,
    yaw NUMERIC(15, 7) NOT NULL,
    posx NUMERIC(15, 7) NOT NULL,
    posy NUMERIC(15, 7) NOT NULL,
    posz NUMERIC(15, 7) NOT NULL,
    hp INT NOT NULL,
    breath INT NOT NULL,
    creation_date TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modification_date TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (name)
);

CREATE TABLE player_metadata (
    player VARCHAR(60) NOT NULL,
    attr VARCHAR(256) NOT NULL,
    value TEXT,
    PRIMARY KEY(player, attr),
    CONSTRAINT player_metadata_fkey FOREIGN KEY (player) REFERENCES player (name) ON DELETE CASCADE
);

CREATE TABLE player_inventories (
    player VARCHAR(60) NOT NULL,
    inv_id INT NOT NULL,
    inv_width INT NOT NULL,
    inv_name TEXT NOT NULL DEFAULT '',
    inv_size INT NOT NULL,
    PRIMARY KEY(player, inv_id),
    CONSTRAINT player_inventories_fkey FOREIGN KEY (player) REFERENCES player (name) ON DELETE CASCADE
);

CREATE TABLE player_inventory_items (
    player VARCHAR(60) NOT NULL,
    inv_id INT NOT NULL,
    slot_id INT NOT NULL,
    item TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(player, inv_id, slot_id),
    CONSTRAINT player_inventory_items_fkey FOREIGN KEY (player) REFERENCES player (name) ON DELETE CASCADE
);

-- Pas de données de démo : les tables démarrent VIDES. C'est le serveur Luanti
-- qui les remplit quand de vrais joueurs se connectent ; service-monde les lit.
-- (GET /monde/joueurs renvoie donc [] tant que personne n'a joué.)

-- Compte strictement lecteur utilisé par service-monde.
-- Le moteur continue d'écrire avec le compte "luanti".
CREATE ROLE monde_reader LOGIN PASSWORD 'monde_reader';
GRANT CONNECT ON DATABASE luanti TO monde_reader;
GRANT USAGE ON SCHEMA public TO monde_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monde_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO monde_reader;
