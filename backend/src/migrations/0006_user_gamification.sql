
CREATE TABLE IF NOT EXISTS fun_facts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title       TEXT    NOT NULL UNIQUE CHECK(LENGTH(title) < 128),
    fact_json   TEXT    NOT NULL, -- json
    min_level   INTEGER NOT NULL DEFAULT 0,
    region_id   INTEGER REFERENCES regions(id) ON DELETE SET NULL -- only supply when in this region, null = all regions
);

CREATE TABLE IF NOT EXISTS seen_facts (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fact_id     INTEGER NOT NULL REFERENCES fun_facts(id) ON DELETE CASCADE,
    seen_count  INTEGER NOT NULL DEFAULT 1 CHECK(seen_count > 0),
    PRIMARY KEY (user_id, fact_id)
);

ALTER TABLE users ADD COLUMN exp INTEGER NOT NULL DEFAULT 0 CHECK (exp >= 0);
ALTER TABLE users ADD COLUMN story TEXT; -- json

CREATE TABLE IF NOT EXISTS level_requirements (
    level       INTEGER PRIMARY KEY,
    min_exp     INTEGER NOT NULL UNIQUE
);

WITH RECURSIVE levels(level, min_exp) AS (
    SELECT 1, 25
    UNION ALL
    SELECT level + 1, min_exp + (level + 1) * 5
    FROM levels
    WHERE level < 1000
)
INSERT INTO level_requirements (level, min_exp)
SELECT level, min_exp
FROM levels;

CREATE TRIGGER trg_update_expert_level
AFTER UPDATE OF exp ON users
FOR EACH ROW
BEGIN
    UPDATE users
    SET expert_level = COALESCE(
        (SELECT MAX(level) FROM level_requirements WHERE min_exp <= NEW.exp),
        0
    )
    WHERE id = NEW.id;
END;
