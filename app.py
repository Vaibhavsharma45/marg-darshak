import os
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "marg_darshak.db")

# ==================== USER LEVELS ====================
LEVELS = {
    'school': {
        'label': 'School Student',
        'hindi': 'स्कूल छात्र',
        'icon': 'fas fa-school',
        'color': '#43e97b',
        'gradient': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        'desc': 'Class 8-12 | Career Exploration',
        'career_categories': ['Technology', 'Creative', 'Science'],
        'gyan_tags': ['student', 'focus', 'duty', 'study'],
        'skill_difficulty': ['Beginner'],
    },
    'college': {
        'label': 'College Student',
        'hindi': 'कॉलेज छात्र',
        'icon': 'fas fa-university',
        'color': '#667eea',
        'gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'desc': 'UG/PG | Skill Building',
        'career_categories': ['Technology', 'Business', 'Creative', 'Science'],
        'gyan_tags': ['career', 'ambition', 'learning', 'growth'],
        'skill_difficulty': ['Beginner', 'Intermediate'],
    },
    'professional': {
        'label': 'Professional',
        'hindi': 'पेशेवर',
        'icon': 'fas fa-briefcase',
        'color': '#f093fb',
        'gradient': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'desc': 'Working Professional | Career Growth',
        'career_categories': ['Technology', 'Business', 'Healthcare', 'Creative'],
        'gyan_tags': ['leadership', 'success', 'karma', 'balance'],
        'skill_difficulty': ['Intermediate', 'Advanced'],
    }
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS careers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, category TEXT, description TEXT,
        roadmap TEXT, skills TEXT, youtube_links TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS gyan_kosh (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter INTEGER, verse_number INTEGER,
        hindi_meaning TEXT, english_meaning TEXT,
        practical_application TEXT, tags TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS learning_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT, title TEXT, url TEXT,
        difficulty TEXT, is_free INTEGER, quality_score REAL
    )''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_level(req):
    return req.args.get('level', req.cookies.get('user_level', 'college'))

# ==================== HOME ====================
@app.route('/')
def index():
    try:
        conn = get_db_connection()
        career_count = conn.execute('SELECT COUNT(*) as count FROM careers').fetchone()['count']
        shloka_count = conn.execute('SELECT COUNT(*) as count FROM gyan_kosh').fetchone()['count']
        resource_count = conn.execute('SELECT COUNT(*) as count FROM learning_resources').fetchone()['count']
        conn.close()
        stats = {'careers': career_count, 'shlokas': shloka_count, 'resources': resource_count}
        return render_template('index.html', stats=stats, levels=LEVELS)
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/select-level')
def select_level():
    return render_template('select_level.html', levels=LEVELS)

# ==================== CAREER ====================
@app.route('/career')
def career_home():
    level = get_level(request)
    return render_template('career/quiz.html', level=level, level_info=LEVELS.get(level, LEVELS['college']))

@app.route('/career/quiz', methods=['GET', 'POST'])
def career_quiz():
    level = get_level(request)
    level_info = LEVELS.get(level, LEVELS['college'])
    if request.method == 'POST':
        try:
            data = request.json
            interests = {k: data.get(k, 0) for k in ['technical','creative','social','analytical','entrepreneurial']}
            sorted_interests = sorted(interests.items(), key=lambda x: x[1], reverse=True)
            category_mapping = {'technical':'Technology','creative':'Creative','social':'Business','analytical':'Technology','entrepreneurial':'Business'}
            conn = get_db_connection()
            careers = []
            for interest, score in sorted_interests[:2]:
                category = category_mapping.get(interest, 'Technology')
                for row in conn.execute('SELECT * FROM careers WHERE category = ? LIMIT 3', (category,)).fetchall():
                    careers.append(dict(row))
            conn.close()
            unique_careers, seen = [], set()
            for c in careers:
                if c['id'] not in seen:
                    unique_careers.append(c); seen.add(c['id'])
            return jsonify({'success': True, 'interests': interests, 'careers': unique_careers[:5]})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return render_template('career/quiz.html', level=level, level_info=level_info)

@app.route('/career/results')
def career_results():
    level = get_level(request)
    return render_template('career/results.html', level=level, level_info=LEVELS.get(level, LEVELS['college']))

@app.route('/career/browse')
def career_browse():
    try:
        level = get_level(request)
        level_info = LEVELS.get(level, LEVELS['college'])
        conn = get_db_connection()
        category = request.args.get('category', 'all')
        if category == 'all':
            careers = conn.execute('SELECT * FROM careers ORDER BY title').fetchall()
        else:
            careers = conn.execute('SELECT * FROM careers WHERE category = ? ORDER BY title', (category,)).fetchall()
        categories = conn.execute('SELECT DISTINCT category FROM careers').fetchall()
        conn.close()
        return render_template('career/browse.html',
            careers=[dict(r) for r in careers],
            categories=[r['category'] for r in categories],
            selected_category=category, level=level, level_info=level_info)
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/career/detail/<int:career_id>')
def career_detail(career_id):
    try:
        level = get_level(request)
        conn = get_db_connection()
        career = conn.execute('SELECT * FROM careers WHERE id = ?', (career_id,)).fetchone()
        conn.close()
        if career:
            return render_template('career/detail.html', career=dict(career),
                level=level, level_info=LEVELS.get(level, LEVELS['college']))
        return "Career not found", 404
    except Exception as e:
        return f"<h2>Error: {e}</h2>", 500

# ==================== GYAN KOSH ====================
@app.route('/gyan')
def gyan_home():
    try:
        level = get_level(request)
        level_info = LEVELS.get(level, LEVELS['college'])
        conn = get_db_connection()
        shloka = conn.execute('SELECT * FROM gyan_kosh ORDER BY RANDOM() LIMIT 1').fetchone()
        conn.close()
        if shloka:
            return render_template('gyan/daily.html', shloka=dict(shloka), level=level, level_info=level_info)
        return "No shlokas found", 500
    except Exception as e:
        return f"<h2>Error: {e}</h2>", 500

@app.route('/gyan/search')
def gyan_search():
    try:
        level = get_level(request)
        query = request.args.get('q', '').strip()
        conn = get_db_connection()
        if query:
            sp = f'%{query}%'
            shlokas = conn.execute('''SELECT * FROM gyan_kosh WHERE hindi_meaning LIKE ?
                OR english_meaning LIKE ? OR practical_application LIKE ? OR tags LIKE ?''',
                (sp, sp, sp, sp)).fetchall()
        else:
            shlokas = conn.execute('SELECT * FROM gyan_kosh ORDER BY chapter, verse_number LIMIT 20').fetchall()
        conn.close()
        return render_template('gyan/search.html', shlokas=[dict(r) for r in shlokas],
            query=query, level=level, level_info=LEVELS.get(level, LEVELS['college']))
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/gyan/detail/<int:shloka_id>')
def gyan_detail(shloka_id):
    try:
        level = get_level(request)
        conn = get_db_connection()
        shloka = conn.execute('SELECT * FROM gyan_kosh WHERE id = ?', (shloka_id,)).fetchone()
        conn.close()
        if shloka:
            return render_template('gyan/detail.html', shloka=dict(shloka),
                level=level, level_info=LEVELS.get(level, LEVELS['college']))
        return "Shloka not found", 404
    except Exception as e:
        return f"Error: {e}", 500

# ==================== SKILL SAATHI ====================
@app.route('/skill')
def skill_home():
    try:
        level = get_level(request)
        level_info = LEVELS.get(level, LEVELS['college'])
        conn = get_db_connection()
        topics = conn.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
        difficulties = level_info['skill_difficulty']
        placeholders = ','.join(['?' for _ in difficulties])
        resources = conn.execute(
            f'SELECT * FROM learning_resources WHERE difficulty IN ({placeholders}) ORDER BY quality_score DESC LIMIT 12',
            difficulties).fetchall()
        if not resources:
            resources = conn.execute('SELECT * FROM learning_resources ORDER BY quality_score DESC LIMIT 12').fetchall()
        conn.close()
        return render_template('skill/browse.html',
            topics=[r['topic'] for r in topics], resources=[dict(r) for r in resources],
            selected_topic='all', selected_difficulty='all', free_only=False,
            level=level, level_info=level_info)
    except Exception as e:
        return f"<h2>Error: {e}</h2>", 500

@app.route('/skill/browse')
def skill_browse():
    try:
        level = get_level(request)
        level_info = LEVELS.get(level, LEVELS['college'])
        topic = request.args.get('topic', 'all')
        difficulty = request.args.get('difficulty', 'all')
        free_only = request.args.get('free', 'false') == 'true'
        conn = get_db_connection()
        query = 'SELECT * FROM learning_resources WHERE 1=1'
        params = []
        if topic != 'all': query += ' AND topic = ?'; params.append(topic)
        if difficulty != 'all': query += ' AND difficulty = ?'; params.append(difficulty)
        if free_only: query += ' AND is_free = 1'
        query += ' ORDER BY quality_score DESC'
        resources = conn.execute(query, params).fetchall()
        topics = conn.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
        conn.close()
        return render_template('skill/browse.html',
            resources=[dict(r) for r in resources], topics=[r['topic'] for r in topics],
            selected_topic=topic, selected_difficulty=difficulty, free_only=free_only,
            level=level, level_info=level_info)
    except Exception as e:
        return f"Error: {e}", 500

# ==================== AI CHATBOT ====================
@app.route('/api/chat-config', methods=['POST'])
def chat_config():
    """Return system prompt + formatted messages for frontend to call Anthropic API"""
    try:
        data = request.json
        level = data.get('level', 'college')
        level_info = LEVELS.get(level, LEVELS['college'])
        system_prompt = f"""You are Marg Darshak AI Guru (मार्ग दर्शक), a wise and warm guide for {level_info['label']} in India.

Your personality:
- Speak in natural Hinglish (mix of Hindi + English) like a knowledgeable dost
- Be warm, encouraging, and practical
- Tailor advice specifically for {level_info['label']}: {level_info['desc']}
- Quote Bhagavad Gita shlokas when relevant, with Sanskrit, meaning, and modern application
- Keep responses focused: 2-4 short paragraphs
- Use 🙏 occasionally

Platform context:
- Career Compass: 25+ careers with roadmaps
- Gyan Kosh: Bhagavad Gita wisdom  
- Skill Saathi: Curated learning resources

End every response with one short encouraging line in Hindi. 🌟"""
        
        return jsonify({
            'success': True,
            'system': system_prompt,
            'level_info': level_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== API STATS ====================
@app.route('/api/stats')
def api_stats():
    try:
        conn = get_db_connection()
        stats = {
            'careers': conn.execute('SELECT COUNT(*) as count FROM careers').fetchone()['count'],
            'shlokas': conn.execute('SELECT COUNT(*) as count FROM gyan_kosh').fetchone()['count'],
            'resources': conn.execute('SELECT COUNT(*) as count FROM learning_resources').fetchone()['count'],
        }
        stats['categories'] = len(conn.execute('SELECT DISTINCT category FROM careers').fetchall())
        conn.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/levels')
def api_levels():
    return jsonify(LEVELS)

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404
@app.errorhandler(500)
def internal_error(e): return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)