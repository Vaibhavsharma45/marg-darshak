import sqlite3
import pandas as pd
import os

def load_csv_data():
    """Load CSV files into database"""
    
    db_path = 'database/marg_darshak.db'
    
    if not os.path.exists(db_path):
        print("❌ Database not found! Run init_db.py first.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # ============ CAREERS ============
        if os.path.exists('data/careers.csv'):
            print("📥 Loading careers...")
            careers_df = pd.read_csv('data/careers.csv')
            
            # Clear existing data (keep table structure)
            cursor.execute('DELETE FROM careers')
            
            # Insert row by row (preserves AUTO_INCREMENT id)
            for _, row in careers_df.iterrows():
                cursor.execute('''
                    INSERT INTO careers (
                        title, category, description, required_skills, 
                        avg_salary_inr, growth_rate, difficulty_level,
                        education_required, top_colleges, job_roles
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['title'], row['category'], row['description'], 
                    row['required_skills'], row['avg_salary_inr'], 
                    row['growth_rate'], row['difficulty_level'],
                    row['education_required'], row['top_colleges'], row['job_roles']
                ))
            
            count = cursor.execute('SELECT COUNT(*) FROM careers').fetchone()[0]
            print(f"✅ Loaded {count} careers")
        else:
            print("⚠️  careers.csv not found")
        
        # ============ GYAN KOSH ============
        if os.path.exists('data/shlokas.csv'):
            print("📥 Loading shlokas...")
            shlokas_df = pd.read_csv('data/shlokas.csv')
            
            cursor.execute('DELETE FROM gyan_kosh')
            
            for _, row in shlokas_df.iterrows():
                cursor.execute('''
                    INSERT INTO gyan_kosh (
                        source, chapter, verse_number, sanskrit_text,
                        hindi_meaning, english_meaning, practical_application,
                        tags, audio_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['source'], row['chapter'], row['verse_number'], 
                    row['sanskrit_text'], row['hindi_meaning'], 
                    row['english_meaning'], row['practical_application'],
                    row['tags'], row['audio_url']
                ))
            
            count = cursor.execute('SELECT COUNT(*) FROM gyan_kosh').fetchone()[0]
            print(f"✅ Loaded {count} shlokas")
        else:
            print("⚠️  shlokas.csv not found")
        
        # ============ LEARNING RESOURCES ============
        if os.path.exists('data/resources.csv'):
            print("📥 Loading learning resources...")
            resources_df = pd.read_csv('data/resources.csv')
            
            cursor.execute('DELETE FROM learning_resources')
            
            for _, row in resources_df.iterrows():
                cursor.execute('''
                    INSERT INTO learning_resources (
                        title, topic, platform, resource_type, url,
                        difficulty, duration_hours, quality_score,
                        language, is_free
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['title'], row['topic'], row['platform'], 
                    row['resource_type'], row['url'], row['difficulty'],
                    row['duration_hours'], row['quality_score'],
                    row['language'], row['is_free']
                ))
            
            count = cursor.execute('SELECT COUNT(*) FROM learning_resources').fetchone()[0]
            print(f"✅ Loaded {count} learning resources")
        else:
            print("⚠️  resources.csv not found")
        
        conn.commit()
        print("\n🎉 All data loaded successfully!")
        
        # ============ VERIFY IDs ============
        print("\n📋 Verification:")
        
        cursor.execute("SELECT id, title FROM careers LIMIT 3")
        print("\nSample careers with IDs:")
        for row in cursor.fetchall():
            print(f"  ✓ ID: {row[0]}, Title: {row[1]}")
        
        cursor.execute("SELECT id, source FROM gyan_kosh LIMIT 2")
        print("\nSample shlokas with IDs:")
        for row in cursor.fetchall():
            print(f"  ✓ ID: {row[0]}, Source: {row[1]}")
        
        cursor.execute("SELECT id, title FROM learning_resources LIMIT 2")
        print("\nSample resources with IDs:")
        for row in cursor.fetchall():
            print(f"  ✓ ID: {row[0]}, Title: {row[1]}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    load_csv_data()