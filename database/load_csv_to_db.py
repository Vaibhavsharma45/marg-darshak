import sqlite3
import pandas as pd

def load_csv_data():
    """Load CSV files into database"""
    
    conn = sqlite3.connect('database/marg_darshak.db')
    
    # Load Careers
    careers_df = pd.read_csv('data/careers.csv')
    careers_df.to_sql('careers', conn, if_exists='replace', index=False)
    print(f"✅ Loaded {len(careers_df)} careers")
    
    # Load Shlokas
    shlokas_df = pd.read_csv('data/shlokas.csv')
    shlokas_df.to_sql('gyan_kosh', conn, if_exists='replace', index=False)
    print(f"✅ Loaded {len(shlokas_df)} shlokas")
    
    # Load Resources
    resources_df = pd.read_csv('data/resources.csv')
    resources_df.to_sql('learning_resources', conn, if_exists='replace', index=False)
    print(f"✅ Loaded {len(resources_df)} learning resources")
    
    conn.close()
    print("\n🎉 All data loaded successfully!")

if __name__ == '__main__':
    load_csv_data()