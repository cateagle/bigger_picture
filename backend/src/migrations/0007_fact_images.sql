CREATE TABLE IF NOT EXISTS helper_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    filepath    TEXT NOT NULL UNIQUE,
    filename    TEXT NOT NULL,
    blake3_hash BLOB NOT NULL CHECK(LENGTH(blake3_hash) = 32)
);

ALTER TABLE fun_facts ADD COLUMN image_id INTEGER REFERENCES helper_images(id) ON DELETE SET NULL;
