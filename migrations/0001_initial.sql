CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    status TEXT,
    date_added TEXT NOT NULL,
    brief_info TEXT,
    detailed_info TEXT,
    keywords TEXT,
    webpage TEXT,
    careers_webpage TEXT,
    careers_webpage_structure TEXT,
    reserved TEXT
);
CREATE TABLE job_listings (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    date_added TEXT NOT NULL,
    date_updated TEXT NOT NULL,
    status TEXT,
    company_name TEXT,
    company_id INTEGER REFERENCES companies(id) ON DELETE RESTRICT,
    score REAL,
    webpage TEXT,
    full_text TEXT,
    reserved TEXT
);
CREATE TABLE job_backlog (
    id INTEGER PRIMARY KEY,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('company', 'job_listing', 'other')),
    source_id INTEGER,
    date_added TEXT NOT NULL,
    date_updated TEXT NOT NULL,
    task_definition TEXT NOT NULL CHECK (length(trim(task_definition)) > 0),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'blocked', 'done', 'cancelled')),
    reserved TEXT
);
CREATE TABLE app_backlog (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('feature', 'bug', 'change')),
    status TEXT NOT NULL DEFAULT 'needs_decision'
        CHECK (status IN ('needs_decision', 'planned', 'in_progress',
                         'awaiting_patch_review', 'done', 'cancelled')),
    date_added TEXT NOT NULL,
    date_updated TEXT NOT NULL,
    details TEXT
);
CREATE INDEX ix_job_listings_company_id ON job_listings(company_id);
CREATE INDEX ix_job_backlog_status ON job_backlog(status);
CREATE INDEX ix_app_backlog_status ON app_backlog(status);
