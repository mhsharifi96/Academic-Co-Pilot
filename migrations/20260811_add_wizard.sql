-- Dynamic wizards: admin-authored guided workflows.
--
-- Parity file only. The application creates these tables itself on startup via
-- Base.metadata.create_all in app/core/database.py:init_models() (there is no
-- migration runner in this project); this script exists so the schema can be
-- applied or reviewed out of band. Every statement is idempotent.
--
-- Order matters: wizards -> wizard_steps -> wizard_runs (references both)
-- -> wizard_messages.

CREATE TABLE IF NOT EXISTS wizards (
    id VARCHAR NOT NULL,
    slug VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    title_en VARCHAR DEFAULT '' NOT NULL,
    title_fa VARCHAR DEFAULT '' NOT NULL,
    short_description_en TEXT DEFAULT '' NOT NULL,
    short_description_fa TEXT DEFAULT '' NOT NULL,
    icon VARCHAR,
    position INTEGER DEFAULT 0 NOT NULL,
    is_published BOOLEAN DEFAULT false NOT NULL,
    enforce_scope_guardrail BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_wizards_slug ON wizards (slug);
CREATE INDEX IF NOT EXISTS ix_wizards_published_position ON wizards (is_published, position);

CREATE TABLE IF NOT EXISTS wizard_steps (
    id VARCHAR NOT NULL,
    wizard_id VARCHAR NOT NULL,
    name_en VARCHAR DEFAULT '' NOT NULL,
    name_fa VARCHAR DEFAULT '' NOT NULL,
    guideline_prompt TEXT NOT NULL,
    max_messages INTEGER,
    position INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (wizard_id) REFERENCES wizards (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_wizard_steps_wizard_id ON wizard_steps (wizard_id);
CREATE INDEX IF NOT EXISTS ix_wizard_steps_wizard_position ON wizard_steps (wizard_id, position);

CREATE TABLE IF NOT EXISTS wizard_runs (
    id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    wizard_id VARCHAR NOT NULL,
    -- == chat_sessions.id == LangGraph thread_id == data/<session_id>/ dir.
    session_id VARCHAR NOT NULL,
    current_step_id VARCHAR,
    status VARCHAR DEFAULT 'active' NOT NULL,
    step_message_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (wizard_id) REFERENCES wizards (id) ON DELETE CASCADE,
    FOREIGN KEY (current_step_id) REFERENCES wizard_steps (id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_wizard_runs_session_id ON wizard_runs (session_id);
CREATE INDEX IF NOT EXISTS ix_wizard_runs_user_id ON wizard_runs (user_id);
CREATE INDEX IF NOT EXISTS ix_wizard_runs_wizard_id ON wizard_runs (wizard_id);
CREATE INDEX IF NOT EXISTS ix_wizard_runs_current_step_id ON wizard_runs (current_step_id);
CREATE INDEX IF NOT EXISTS ix_wizard_runs_user_status ON wizard_runs (user_id, status);
CREATE INDEX IF NOT EXISTS ix_wizard_runs_user_wizard_status ON wizard_runs (user_id, wizard_id, status);

CREATE TABLE IF NOT EXISTS wizard_messages (
    id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    -- The step that was current when this turn happened.
    step_id VARCHAR,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (run_id) REFERENCES wizard_runs (id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES wizard_steps (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_wizard_messages_run_id ON wizard_messages (run_id);
CREATE INDEX IF NOT EXISTS ix_wizard_messages_step_id ON wizard_messages (step_id);
CREATE INDEX IF NOT EXISTS ix_wizard_messages_run_created ON wizard_messages (run_id, created_at);
