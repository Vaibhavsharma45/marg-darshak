-- Careers Table
CREATE TABLE IF NOT EXISTS careers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    required_skills TEXT,
    avg_salary_inr INTEGER,
    growth_rate VARCHAR(20),
    difficulty_level VARCHAR(20),
    education_required VARCHAR(100),
    top_colleges TEXT,
    job_roles TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gyan Kosh (Spiritual Wisdom)
CREATE TABLE IF NOT EXISTS gyan_kosh (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source VARCHAR(50),
    chapter INTEGER,
    verse_number INTEGER,
    sanskrit_text TEXT NOT NULL,
    hindi_meaning TEXT,
    english_meaning TEXT,
    practical_application TEXT,
    tags TEXT,
    audio_url VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Learning Resources
CREATE TABLE IF NOT EXISTS learning_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    topic VARCHAR(100),
    platform VARCHAR(50),
    resource_type VARCHAR(20),
    url TEXT NOT NULL,
    difficulty VARCHAR(20),
    duration_hours INTEGER,
    quality_score FLOAT,
    language VARCHAR(20),
    is_free BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Quiz Results (Optional - for analytics)
CREATE TABLE IF NOT EXISTS quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interests_analytical INTEGER,
    interests_creative INTEGER,
    interests_social INTEGER,
    interests_technical INTEGER,
    interests_entrepreneurial INTEGER,
    recommended_careers TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);