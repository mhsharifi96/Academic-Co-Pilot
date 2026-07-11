-- Add the provider PDF download queue table.
-- This migration is idempotent so it can be applied safely on fresh and
-- already-upgraded databases.

CREATE TABLE IF NOT EXISTS download_jobs (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR NOT NULL,
    doi VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'QUEUED',
    service_tier VARCHAR NOT NULL,
    request_number INTEGER NOT NULL,
    priority_round INTEGER,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    target_deadline TIMESTAMPTZ NOT NULL,
    failure_code VARCHAR,
    file_path VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_download_jobs_user_id
    ON download_jobs (user_id);

CREATE INDEX IF NOT EXISTS ix_download_jobs_session_id
    ON download_jobs (session_id);

CREATE INDEX IF NOT EXISTS ix_download_jobs_doi
    ON download_jobs (doi);

CREATE INDEX IF NOT EXISTS ix_download_jobs_status_available
    ON download_jobs (status, available_at);

CREATE INDEX IF NOT EXISTS ix_download_jobs_user_created
    ON download_jobs (user_id, created_at);
