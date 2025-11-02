import sqlite3

# Connect to the database (will create if not exists)
conn = sqlite3.connect('database/marg_darshak.db')
cursor = conn.cursor()

# Create example tables (you can adjust as needed)
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    score INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS careers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_name TEXT,
    description TEXT,
    skills TEXT,
    roadmap TEXT
)
''')

conn.commit()
conn.close()

print("✅ Database tables created successfully!")
