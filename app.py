from flask import Flask, render_template, request, jsonify
import sqlite3
import pandas as pd
from datetime import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('database/marg_darshak.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==================== HOME PAGE ====================
@app.route('/')
def index():
    """Homepage with 3 main modules"""
    
    # Get some stats for homepage
    conn = get_db_connection()
    
    career_count = conn.execute('SELECT COUNT(*) as count FROM careers').fetchone()['count']
    shloka_count = conn.execute('SELECT COUNT(*) as count FROM gyan_kosh').fetchone()['count']
    resource_count = conn.execute('SELECT COUNT(*) as count FROM learning_resources').fetchone()['count']
    
    conn.close()
    
    stats = {
        'careers': career_count,
        'shlokas': shloka_count,
        'resources': resource_count
    }
    
    return render_template('index.html', stats=stats)

# ==================== CAREER MODULE ====================
@app.route('/career')
def career_home():
    """Career guidance homepage"""
    return render_template('career/quiz.html')

@app.route('/career/quiz', methods=['GET', 'POST'])
def career_quiz():
    """Career interest quiz"""
    if request.method == 'POST':
        # Get quiz responses
        data = request.json
        
        # Simple scoring logic
        interests = {
            'technical': data.get('technical', 0),
            'creative': data.get('creative', 0),
            'social': data.get('social', 0),
            'analytical': data.get('analytical', 0),
            'entrepreneurial': data.get('entrepreneurial', 0)
        }
        
        # Find top 2 interests
        sorted_interests = sorted(interests.items(), key=lambda x: x[1], reverse=True)[:2]
        top_categories = [item[0] for item in sorted_interests]
        
        # Get matching careers from database
        conn = get_db_connection()
        careers = []
        
        # Map interests to career categories
        category_mapping = {
            'technical': 'Technology',
            'creative': 'Creative',
            'social': 'Business',
            'analytical': 'Technology',
            'entrepreneurial': 'Business'
        }
        
        for interest in top_categories:
            category = category_mapping.get(interest, 'Technology')
            results = conn.execute(
                'SELECT * FROM careers WHERE category = ? LIMIT 3',
                (category,)
            ).fetchall()
            careers.extend([dict(row) for row in results])
        
        conn.close()
        
        return jsonify({
            'success': True,
            'interests': interests,
            'careers': careers[:5]  # Top 5 careers
        })
    
    return render_template('career/quiz.html')

@app.route('/career/results/<int:career_id>')
def career_details(career_id):
    """Detailed career information"""
    conn = get_db_connection()
    career = conn.execute('SELECT * FROM careers WHERE id = ?', (career_id,)).fetchone()
    conn.close()
    
    if career:
        return render_template('career/results.html', career=dict(career))
    return "Career not found", 404

@app.route('/career/browse')
def career_browse():
    """Browse all careers"""
    conn = get_db_connection()
    
    category = request.args.get('category', 'all')
    
    if category == 'all':
        careers = conn.execute('SELECT * FROM careers ORDER BY title').fetchall()
    else:
        careers = conn.execute('SELECT * FROM careers WHERE category = ? ORDER BY title', (category,)).fetchall()
    
    # Get unique categories for filter
    categories = conn.execute('SELECT DISTINCT category FROM careers').fetchall()
    
    conn.close()
    
    return render_template('career/browse.html', 
                         careers=[dict(row) for row in careers],
                         categories=[row['category'] for row in categories],
                         selected_category=category)
@app.route('/career/results')
def career_results():
    """Display career quiz results"""
    return render_template('career/results.html')

@app.route('/career/roadmap/<int:career_id>')
def career_roadmap(career_id):
    """Career roadmap details"""
    conn = get_db_connection()
    career = conn.execute('SELECT * FROM careers WHERE id = ?', (career_id,)).fetchone()
    conn.close()
    
    if career:
        return render_template('career/roadmap.html', career=dict(career))
    return "Career not found", 404

# ==================== GYAN KOSH MODULE ====================
@app.route('/gyan')
def gyan_home():
    """Gyan Kosh homepage - Daily Shloka"""
    conn = get_db_connection()
    
    # Get random shloka for "daily" wisdom
    shloka = conn.execute('SELECT * FROM gyan_kosh ORDER BY RANDOM() LIMIT 1').fetchone()
    
    conn.close()
    
    return render_template('gyan/daily.html', shloka=dict(shloka))

@app.route('/gyan/search')
def gyan_search():
    """Search shlokas"""
    query = request.args.get('q', '').strip()
    
    conn = get_db_connection()
    
    if query:
        # Search in multiple fields
        search_pattern = f'%{query}%'
        shlokas = conn.execute('''
            SELECT * FROM gyan_kosh 
            WHERE hindi_meaning LIKE ? 
            OR english_meaning LIKE ? 
            OR practical_application LIKE ?
            OR tags LIKE ?
        ''', (search_pattern, search_pattern, search_pattern, search_pattern)).fetchall()
    else:
        # Show all if no query
        shlokas = conn.execute('SELECT * FROM gyan_kosh ORDER BY chapter, verse_number').fetchall()
    
    conn.close()
    
    return render_template('gyan/search.html', 
                         shlokas=[dict(row) for row in shlokas],
                         query=query)

@app.route('/gyan/detail/<int:shloka_id>')
def gyan_detail(shloka_id):
    """Detailed shloka view"""
    conn = get_db_connection()
    shloka = conn.execute('SELECT * FROM gyan_kosh WHERE id = ?', (shloka_id,)).fetchone()
    conn.close()
    
    if shloka:
        return render_template('gyan/detail.html', shloka=dict(shloka))
    return "Shloka not found", 404

# ==================== SKILL SAATHI MODULE ====================
@app.route('/skill')
def skill_home():
    """Skill Saathi homepage"""
    conn = get_db_connection()
    
    # Get topics and featured resources
    topics = conn.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
    featured = conn.execute('SELECT * FROM learning_resources WHERE quality_score >= 4.5 LIMIT 6').fetchall()
    
    conn.close()
    
    return render_template('skill/browse.html', 
                         topics=[row['topic'] for row in topics],
                         featured=[dict(row) for row in featured])

@app.route('/skill/browse')
def skill_browse():
    """Browse learning resources with filters"""
    topic = request.args.get('topic', 'all')
    difficulty = request.args.get('difficulty', 'all')
    free_only = request.args.get('free', 'false') == 'true'
    
    conn = get_db_connection()
    
    # Build query based on filters
    query = 'SELECT * FROM learning_resources WHERE 1=1'
    params = []
    
    if topic != 'all':
        query += ' AND topic = ?'
        params.append(topic)
    
    if difficulty != 'all':
        query += ' AND difficulty = ?'
        params.append(difficulty)
    
    if free_only:
        query += ' AND is_free = 1'
    
    query += ' ORDER BY quality_score DESC'
    
    resources = conn.execute(query, params).fetchall()
    topics = conn.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
    
    conn.close()
    
    return render_template('skill/browse.html',
                         resources=[dict(row) for row in resources],
                         topics=[row['topic'] for row in topics],
                         selected_topic=topic,
                         selected_difficulty=difficulty,
                         free_only=free_only)

# ==================== API ROUTES ====================
@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    conn = get_db_connection()
    
    stats = {
        'careers': conn.execute('SELECT COUNT(*) as count FROM careers').fetchone()['count'],
        'shlokas': conn.execute('SELECT COUNT(*) as count FROM gyan_kosh').fetchone()['count'],
        'resources': conn.execute('SELECT COUNT(*) as count FROM learning_resources').fetchone()['count'],
        'categories': len(conn.execute('SELECT DISTINCT category FROM careers').fetchall())
    }
    
    conn.close()
    
    return jsonify(stats)

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

# =========================favicon.ico ROUTE =========================
# Add this route in app.py (after other routes, before error handlers)

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    from flask import send_from_directory
    import os
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

# ==================== RUN APP ====================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)