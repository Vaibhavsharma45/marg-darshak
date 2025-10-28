import sqlite3
import os

def init_database():
    """Initialize SQLite database with schema"""
    
    db_path = 'database/marg_darshak.db'
    
    # Create database directory if not exists
    os.makedirs('database', exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read and execute schema
    with open('database/schema.sql', 'r', encoding='utf-8') as f:
        schema = f.read()
        cursor.executescript(schema)
    
    print("✅ Database initialized successfully!")
    
    # Insert sample data
    insert_sample_data(conn)
    
    conn.commit()
    conn.close()
    print("✅ Sample data inserted!")

def insert_sample_data(conn):
    """Insert sample data for testing"""
    cursor = conn.cursor()
    
    # Sample Careers
    careers = [
        ('Data Scientist', 'Technology', 'Analyze data to extract insights using ML and statistics', 
         'Python, ML, Statistics, SQL', 1200000, 'Very High', 'Hard', 
         'BTech/MSc in CS/Stats', 'IIT, IIIT, Top tier colleges', 
         'Data Analyst, ML Engineer, Data Engineer'),
        
        ('Software Developer', 'Technology', 'Build applications and software solutions',
         'Programming, DSA, Problem Solving', 800000, 'High', 'Medium',
         'BTech/BCA in CS', 'IIT, NIT, IIIT', 
         'Backend Developer, Frontend Developer, Full Stack'),
        
        ('Digital Marketing', 'Business', 'Promote products/services through digital channels',
         'SEO, Content, Analytics, Social Media', 500000, 'High', 'Easy',
         'Any Graduate + Certification', 'Any college', 
         'SEO Specialist, Content Marketer, Social Media Manager'),
    ]
    
    cursor.executemany('''
        INSERT INTO careers (title, category, description, required_skills, 
                           avg_salary_inr, growth_rate, difficulty_level,
                           education_required, top_colleges, job_roles)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', careers)
    
    # Sample Gyan Kosh
    shlokas = [
        ('Bhagavad Gita', 2, 47, 
         'कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।',
         'तुम्हारा अधिकार केवल कर्म पर है, फल पर कभी नहीं।',
         'You have the right to perform your duty, but not to the fruits of action.',
         'Focus on your work without worrying about results. Do your best in studies/job without stressing about outcomes.',
         'karma, duty, detachment',
         'https://www.youtube.com/watch?v=sample'),
        
        ('Bhagavad Gita', 6, 5,
         'उद्धरेदात्मनात्मानं नात्मानमवसादयेत्।',
         'अपने द्वारा अपना उद्धार करो, अपने को नीचे मत गिराओ।',
         'Elevate yourself through your own efforts, do not degrade yourself.',
         'Self-improvement is your responsibility. No one else can uplift you - take charge of your growth.',
         'self-improvement, motivation, responsibility',
         'https://www.youtube.com/watch?v=sample'),
    ]
    
    cursor.executemany('''
        INSERT INTO gyan_kosh (source, chapter, verse_number, sanskrit_text,
                              hindi_meaning, english_meaning, practical_application,
                              tags, audio_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', shlokas)
    
    # Sample Learning Resources
    resources = [
        ('Python for Beginners', 'Programming', 'YouTube', 'Video', 
         'https://youtube.com/playlist?list=sample', 'Beginner', 20, 4.7, 'English', True),
        
        ('Data Science Full Course', 'Data Science', 'YouTube', 'Video',
         'https://youtube.com/watch?v=sample', 'Intermediate', 40, 4.8, 'English', True),
        
        ('Machine Learning A-Z', 'Machine Learning', 'Udemy', 'Course',
         'https://www.udemy.com/course/sample', 'Intermediate', 44, 4.6, 'English', False),
    ]
    
    cursor.executemany('''
        INSERT INTO learning_resources (title, topic, platform, resource_type,
                                       url, difficulty, duration_hours, quality_score,
                                       language, is_free)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', resources)

if __name__ == '__main__':
    init_database()