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
