-- Records a claimed daily-quest reward, so each (user, quest, day) grants XP at
-- most once. Quest definitions and progress are not stored (progress is counted
-- live from the annotation tables); only the claim is persisted here.
CREATE TABLE IF NOT EXISTS quest_claims (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quest_key     TEXT    NOT NULL,
    day_start_ms  INTEGER NOT NULL, -- local-midnight unix millis identifying the quest day
    reward_exp    INTEGER NOT NULL,
    created_at    INTEGER NOT NULL, -- unix millis
    UNIQUE (user_id, quest_key, day_start_ms)
);

CREATE INDEX IF NOT EXISTS idx_quest_claims_user_day
    ON quest_claims (user_id, day_start_ms);
