# create_tables.py
import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create the careers table (same structure as your main code)
c.execute('''CREATE TABLE IF NOT EXISTS careers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    roadmap TEXT,
    skills TEXT,
    youtube_links TEXT
)''')

print("✅ Table created successfully!")
conn.commit()
conn.close()
