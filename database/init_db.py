import sqlite3
import os

def init_database():
    """Initialize SQLite database with proper schema"""
    
    db_path = 'database/marg_darshak.db'
    
    # Create database directory
    os.makedirs('database', exist_ok=True)
    
    # Delete old database if exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️  Old database deleted")
    
    # Connect and create tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("📦 Creating tables...")
    
    # Careers table with AUTO INCREMENT id
    cursor.execute('''
        CREATE TABLE careers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            description TEXT,
            required_skills TEXT,
            avg_salary_inr INTEGER,
            growth_rate TEXT,
            difficulty_level TEXT,
            education_required TEXT,
            top_colleges TEXT,
            job_roles TEXT
        )
    ''')
    print("✅ Careers table created")
    
    # Gyan Kosh table
    cursor.execute('''
        CREATE TABLE gyan_kosh (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            chapter INTEGER,
            verse_number INTEGER,
            sanskrit_text TEXT,
            hindi_meaning TEXT,
            english_meaning TEXT,
            practical_application TEXT,
            tags TEXT,
            audio_url TEXT
        )
    ''')
    print("✅ Gyan Kosh table created")
    
    # Learning Resources table
    cursor.execute('''
        CREATE TABLE learning_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            topic TEXT,
            platform TEXT,
            resource_type TEXT,
            url TEXT,
            difficulty TEXT,
            duration_hours INTEGER,
            quality_score REAL,
            language TEXT,
            is_free INTEGER
        )
    ''')
    print("✅ Learning Resources table created")
    
    conn.commit()
    conn.close()
    
    print("\n🎉 Database initialized successfully!")
    print(f"📍 Location: {os.path.abspath(db_path)}")

if __name__ == '__main__':
    init_database()