-- Create the 'users' table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE,
    hashed_password TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE
);

-- Create the 'jobs' table
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    company VARCHAR(255),
    email VARCHAR(255) NULL,
    url VARCHAR(512) UNIQUE NULL,
    description TEXT,
    role VARCHAR(255) NULL,
    location VARCHAR(255) NULL,
    country VARCHAR(255) NULL,
    platform VARCHAR(255) NULL,
    job_type VARCHAR(255) NULL,
    workplace_type VARCHAR(255) NULL,
    posted_date DATE NULL,
    salary VARCHAR(255) NULL,
    skills JSON NULL,
    created_at VARCHAR(255) DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS')
);

-- Create the 'scores' table
CREATE TABLE IF NOT EXISTS scores (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    final_score FLOAT,
    trust_tier INTEGER,
    flags JSON,
    raw_threats JSON
);

-- Indexes for performance optimizations
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_role ON jobs(role);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location);
CREATE INDEX IF NOT EXISTS idx_jobs_country ON jobs(country);
CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(platform);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_workplace_type ON jobs(workplace_type);
CREATE INDEX IF NOT EXISTS idx_scores_job_id ON scores(job_id);

-- ──────────────────────────────────────────────────────────
-- USER-JOB INTERACTIONS (Supabase RLS-protected)
-- ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_job_interactions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    applied BOOLEAN DEFAULT FALSE,
    rejected BOOLEAN DEFAULT FALSE,
    created_at VARCHAR(255) DEFAULT TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
    UNIQUE(user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON user_job_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_job_id ON user_job_interactions(job_id);

-- Enable Row Level Security
ALTER TABLE user_job_interactions ENABLE ROW LEVEL SECURITY;

-- Users can only see and modify their own interactions
CREATE POLICY "Users can view own interactions"
    ON user_job_interactions FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own interactions"
    ON user_job_interactions FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own interactions"
    ON user_job_interactions FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own interactions"
    ON user_job_interactions FOR DELETE
    USING (user_id = auth.uid());

-- Service-role bypass (for backend API running with SERVICE_ROLE key)
-- No policy needed — the service_role key circumvents RLS by default.
