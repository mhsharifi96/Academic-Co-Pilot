-- Site-wide settings an admin can flip at runtime (first switch: whether new
-- users may register).
--
-- Parity file only. The application creates this table itself on startup via
-- Base.metadata.create_all in app/core/database.py:init_models() (there is no
-- migration runner in this project); this script exists so the schema can be
-- applied or reviewed out of band. Every statement is idempotent.

CREATE TABLE IF NOT EXISTS site_settings (
    id VARCHAR NOT NULL,
    registration_open BOOLEAN DEFAULT true NOT NULL,
    updated_at TIMESTAMPTZ,
    PRIMARY KEY (id)
);

-- The row is a singleton keyed 'global'; the app inserts it lazily on first
-- read, so seeding here is optional but keeps an out-of-band apply complete.
INSERT INTO site_settings (id, registration_open, updated_at)
VALUES ('global', true, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO NOTHING;
