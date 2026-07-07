PRAGMA FOREIGN_KEYS = 'on';

CREATE TABLE IF NOT EXISTS field_documentation (
    table_name  TEXT    NOT NULL,
    column_name TEXT    NOT NULL,
    description TEXT    CHECK(description IS NULL OR LENGTH(description) < 1024),
    PRIMARY KEY (table_name, column_name)
);

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    username    TEXT    NOT NULL UNIQUE(LOWER(username)),
    role        TEXT    NOT NULL CHECK(role IN ('annotator', 'scientist', 'admin'),
    expert_level INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS labels (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    scope       TEXT    NOT NULL CHECK(LENGTH(scope) < 128),
    title       TEXT    NOT NULL CHECK(LENGTH(title) < 128),
    description TEXT    CHECK(description IS NULL OR LENGTH(description) < 1024),
    UNIQUE (scope, title)
);

CREATE TABLE IF NOT EXISTS cameras (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title       TEXT    NOT NULL UNIQUE CHECK(LENGTH(title) < 128),
    metadata    TEXT, -- json
    description TEXT    CHECK(description IS NULL OR LENGTH(description) < 1024)
);

CREATE TABLE IF NOT EXISTS regions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title       TEXT    NOT NULL UNIQUE CHECK(LENGTH(title) < 128),
    metadata    TEXT, -- json
    description TEXT    CHECK(description IS NULL OR LENGTH(description) < 1024)
);

CREATE TABLE IF NOT EXISTS dives (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title       TEXT    NOT NULL UNIQUE CHECK(LENGTH(title) < 128),
    metadata    TEXT, -- json
    description TEXT    CHECK(description IS NULL OR LENGTH(description) < 1024),
    region_id   INTEGER NOT NULL REFERENCES regions(id) ON DELETE RESTRICT,
    camera_id   INTEGER NOT NULL REFERENCES cameras(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS image_statuses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title       TEXT    NOT NULL UNIQUE CHECK(LENGTH(title) < 128),
    metadata    TEXT, -- json
    description TEXT    CHECK(description IS NULL OR LENGTH(description) < 1024)
);

CREATE TABLE IF NOT EXISTS pair_statuses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title       TEXT    NOT NULL UNIQUE CHECK(LENGTH(title) < 128),
    metadata    TEXT, -- json
    description TEXT    CHECK(description IS NULL OR LENGTH(description) < 1024)
);

CREATE TABLE IF NOT EXISTS images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    filename    TEXT    NOT NULL CHECK(LENGTH(filename) < 256),
    filepath    TEXT    NOT NULL UNIQUE CHECK(LENGTH(filepath) < 1024),
    dive_id     INTEGER NOT NULL REFERENCES dives(id) ON DELETE RESTRICT,
    status_id   INTEGER REFERENCES image_statuses(id) ON DELETE RESTRICT,
    size_x      INTEGER NOT NULL CHECK(size_x > 0),
    size_y      INTEGER NOT NULL CHECK(size_y > 0),
    camera_pos  TEXT, -- json
    metadata    TEXT, -- json
    difficulty  INTEGER,
    priority    INTEGER
);

CREATE TABLE IF NOT EXISTS image_pairs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    image1_id   INTEGER NOT NULL REFERENCES images(id) ON DELETE RESTRICT,
    image2_id   INTEGER NOT NULL REFERENCES images(id) ON DELETE RESTRICT,
    difficulty  INTEGER,
    priority    INTEGER,
    status_id   INTEGER REFERENCES pair_statuses(id) ON DELETE RESTRICT,
    UNIQUE (image1_id, image2_id),
    CHECK (image1_id < image2_id) -- this prevents self pairing and bidirectional uniqueness
);

CREATE TABLE IF NOT EXISTS point_annotations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    pair_id     INTEGER NOT NULL REFERENCES image_pairs(id) ON DELETE RESTRICT,
    label_id    INTEGER REFERENCES labels(id) ON DELETE RESTRICT,
    x1          INTEGER NOT NULL CHECK(x1 >=0),
    y1          INTEGER NOT NULL CHECK(y1 >=0),
    x2          INTEGER NOT NULL CHECK(x2 >=0),
    y2          INTEGER NOT NULL CHECK(y2 >=0),
    expert_level INTEGER NOT NULL, -- copied from expert level of user
    confidence  REAL
);

-- idea: trigger that looks up the x_size and y_size for both images and prevents coordinates larger than the image sizes
