import os
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, jsonify, session, g)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'database', 'marg_darshak.db')

# ═══════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════
LEVELS = {
    'school': {
        'label': 'School Student', 'hindi': 'स्कूल छात्र',
        'icon': 'fas fa-school', 'color': '#43e97b',
        'gradient': 'linear-gradient(135deg,#43e97b,#38f9d7)',
        'desc': 'Class 6–12 | Explore, Discover, Dream',
        'classes': {
            '6':  'Class 6',  '7':  'Class 7',  '8':  'Class 8',
            '9':  'Class 9',  '10': 'Class 10',
            '11': 'Class 11', '12': 'Class 12',
        },
        'boards': ['CBSE','ICSE','State Board','IB','NIOS'],
    },
    'college': {
        'label': 'College Student', 'hindi': 'कॉलेज छात्र',
        'icon': 'fas fa-university', 'color': '#667eea',
        'gradient': 'linear-gradient(135deg,#667eea,#764ba2)',
        'desc': 'UG / PG | Build Skills, Shape Future',
        'streams': ['Engineering','Medical','Commerce','Arts','Science',
                    'Law','Design','Management','Other'],
        'years':   ['1st Year','2nd Year','3rd Year','4th Year','PG'],
    },
    'professional': {
        'label': 'Professional', 'hindi': 'पेशेवर',
        'icon': 'fas fa-briefcase', 'color': '#f093fb',
        'gradient': 'linear-gradient(135deg,#f093fb,#f5576c)',
        'desc': 'Working Professional | Level Up, Lead',
        'experience': ['0–1 yr','1–3 yrs','3–5 yrs','5–10 yrs','10+ yrs'],
        'domains':    ['Technology','Finance','Healthcare','Marketing',
                       'Education','Legal','Design','Operations','Other'],
    },
}

SCHOOL_GOALS = {
    'doctor':    {'label':'Doctor / Medical','icon':'🩺',
                  'subjects':['Biology','Chemistry','Physics'],
                  'exam':'NEET','path':'PCB → MBBS / BDS / BAMS'},
    'engineer':  {'label':'Engineer','icon':'⚙️',
                  'subjects':['Maths','Physics','Chemistry'],
                  'exam':'JEE','path':'PCM → BTech / BE'},
    'ca':        {'label':'CA / Finance','icon':'📊',
                  'subjects':['Accountancy','Economics','Maths'],
                  'exam':'CA Foundation','path':'Commerce → CA / CMA'},
    'lawyer':    {'label':'Lawyer','icon':'⚖️',
                  'subjects':['Social Science','English','Political Science'],
                  'exam':'CLAT','path':'Any Stream → LLB / BA LLB'},
    'designer':  {'label':'Designer / Artist','icon':'🎨',
                  'subjects':['Fine Arts','Computer','English'],
                  'exam':'NID / NIFT','path':'Any Stream → Design Degree'},
    'scientist':  {'label':'Scientist / Researcher','icon':'🔬',
                  'subjects':['Science','Maths'],
                  'exam':'KVPY / IISc','path':'PCM/PCB → BSc Research'},
    'entrepreneur':{'label':'Entrepreneur','icon':'🚀',
                  'subjects':['Business Studies','Economics'],
                  'exam':'None specific','path':'Any → MBA / Self Build'},
    'teacher':   {'label':'Teacher / Professor','icon':'📚',
                  'subjects':['Any core subject'],
                  'exam':'CTET / NET','path':'Any → BEd / NET'},
    'ias':       {'label':'IAS / Civil Services','icon':'🏛️',
                  'subjects':['History','Geography','Polity'],
                  'exam':'UPSC','path':'Any → Graduation → UPSC'},
    'athlete':   {'label':'Athlete / Sports','icon':'🏆',
                  'subjects':['Physical Education'],
                  'exam':'SAI / State trials','path':'Any → Sports Academy'},
}

COLLEGE_GOALS = {
    'software_engineer': '💻 Software Engineer',
    'data_scientist':    '📊 Data Scientist / ML Engineer',
    'product_manager':   '🎯 Product Manager',
    'startup_founder':   '🚀 Startup Founder',
    'finance_analyst':   '💰 Finance / Investment Analyst',
    'doctor_pg':         '🩺 Doctor (PG / Specialisation)',
    'civil_services':    '🏛️ Civil Services (UPSC)',
    'researcher':        '🔬 Researcher / PhD',
    'designer_ux':       '🎨 UX / Product Designer',
    'content_creator':   '🎬 Content Creator / YouTuber',
    'lawyer_practice':   '⚖️ Practicing Lawyer',
    'ngo_social':        '🌱 NGO / Social Impact',
}

PROFESSIONAL_GOALS = {
    'senior_role':     '📈 Get Senior / Lead Role',
    'switch_domain':   '🔄 Switch Domain / Industry',
    'start_business':  '🚀 Start Own Business',
    'higher_studies':  '🎓 Higher Studies / MBA',
    'work_abroad':     '✈️  Work Abroad',
    'freelance':       '💼 Go Freelance',
    'certification':   '📜 Get Certified / Upskill',
    'leadership':      '👑 Move into Leadership',
}

LANGUAGES = {
    'en': {'label': 'English', 'flag': '🇬🇧'},
    'hi': {'label': 'हिंदी / Hinglish', 'flag': '🇮🇳'},
}

# ═══════════════════════════════════════════════
#  DB HELPERS
# ═══════════════════════════════════════════════
def get_db():
    if 'db' not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        username  TEXT UNIQUE NOT NULL,
        password  TEXT NOT NULL,
        level     TEXT DEFAULT 'college',
        class_std TEXT,
        board     TEXT,
        stream    TEXT,
        year      TEXT,
        experience TEXT,
        domain    TEXT,
        goal      TEXT,
        language  TEXT DEFAULT 'en',
        onboarded INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Careers
    c.execute('''CREATE TABLE IF NOT EXISTS careers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, category TEXT, description TEXT,
        required_skills TEXT, avg_salary_inr INTEGER,
        growth_rate TEXT, difficulty_level TEXT,
        education_required TEXT, top_colleges TEXT, job_roles TEXT
    )''')

    # Gyan Kosh
    c.execute('''CREATE TABLE IF NOT EXISTS gyan_kosh (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT, chapter INTEGER, verse_number INTEGER,
        sanskrit_text TEXT, hindi_meaning TEXT, english_meaning TEXT,
        practical_application TEXT, tags TEXT, audio_url TEXT
    )''')

    # Learning Resources
    c.execute('''CREATE TABLE IF NOT EXISTS learning_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, topic TEXT, platform TEXT, resource_type TEXT,
        url TEXT, difficulty TEXT, duration_hours INTEGER,
        quality_score REAL, language TEXT, is_free INTEGER,
        board TEXT, class_std TEXT, level TEXT
    )''')

    conn.commit()
    conn.close()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(user_id):
    return get_db().execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()

# ═══════════════════════════════════════════════
#  AUTH DECORATOR
# ═══════════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session and not session.get('guest'):
            return redirect(url_for('auth'))
        return f(*args, **kwargs)
    return decorated

def onboarding_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('guest'):
            return f(*args, **kwargs)
        if 'user_id' in session:
            user = get_user(session['user_id'])
            if user and not user['onboarded']:
                return redirect(url_for('onboarding'))
        return f(*args, **kwargs)
    return decorated

# ═══════════════════════════════════════════════
#  CONTEXT PROCESSOR — injects user into all templates
# ═══════════════════════════════════════════════
@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = get_user(session['user_id'])
    is_guest = session.get('guest', False)
    lang = (dict(user)['language'] if user else session.get('lang', 'en'))
    level_key = (dict(user)['level'] if user else session.get('level', 'college'))
    level_info = LEVELS.get(level_key, LEVELS['college'])
    return dict(
        current_user=dict(user) if user else None,
        is_guest=is_guest,
        lang=lang,
        levels=LEVELS,
        level=level_key,
        level_info=level_info,
        languages=LANGUAGES,
    )

# ═══════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if 'user_id' in session or session.get('guest'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        action   = request.form.get('action')
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        db = get_db()

        if action == 'login':
            user = db.execute(
                'SELECT * FROM users WHERE username=? AND password=?',
                (username, hash_pw(password))
            ).fetchone()
            if user:
                session['user_id'] = user['id']
                session.pop('guest', None)
                if not user['onboarded']:
                    return redirect(url_for('onboarding'))
                return redirect(url_for('dashboard'))
            return render_template('auth.html', error='login',
                                   msg='Galat username ya password! 🙈')

        elif action == 'signup':
            if len(username) < 3:
                return render_template('auth.html', error='signup',
                                       msg='Username kam se kam 3 characters ka hona chahiye')
            if len(password) < 6:
                return render_template('auth.html', error='signup',
                                       msg='Password 6+ characters ka hona chahiye')
            existing = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
            if existing:
                return render_template('auth.html', error='signup',
                                       msg='Yeh username already le liya gaya hai! Try another.')
            db.execute(
                'INSERT INTO users (username, password) VALUES (?,?)',
                (username, hash_pw(password))
            )
            db.commit()
            user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
            session['user_id'] = user['id']
            session.pop('guest', None)
            return redirect(url_for('onboarding'))

    return render_template('auth.html')

@app.route('/guest')
def guest_login():
    session.clear()
    session['guest'] = True
    session['level'] = 'college'
    session['lang']  = 'en'
    return redirect(url_for('onboarding'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth'))

# ═══════════════════════════════════════════════
#  ONBOARDING
# ═══════════════════════════════════════════════
@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    if request.method == 'POST':
        data = request.json or request.form
        level      = data.get('level', 'college')
        class_std  = data.get('class_std', '')
        board      = data.get('board', '')
        stream     = data.get('stream', '')
        year       = data.get('year', '')
        experience = data.get('experience', '')
        domain     = data.get('domain', '')
        goal       = data.get('goal', '')
        language   = data.get('language', 'en')

        if session.get('guest'):
            session.update({'level': level, 'class_std': class_std,
                            'board': board, 'stream': stream,
                            'goal': goal, 'lang': language,
                            'guest_onboarded': True})
            return jsonify({'success': True, 'redirect': url_for('dashboard')})

        db = get_db()
        db.execute('''UPDATE users SET level=?,class_std=?,board=?,stream=?,
                      year=?,experience=?,domain=?,goal=?,language=?,onboarded=1
                      WHERE id=?''',
                   (level, class_std, board, stream,
                    year, experience, domain, goal, language,
                    session['user_id']))
        db.commit()
        return jsonify({'success': True, 'redirect': url_for('dashboard')})

    return render_template('onboarding.html',
                           school_goals=SCHOOL_GOALS,
                           college_goals=COLLEGE_GOALS,
                           professional_goals=PROFESSIONAL_GOALS)

# ═══════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════
@app.route('/')
@app.route('/dashboard')
@login_required
@onboarding_required
def dashboard():
    db = get_db()
    try:
        careers   = db.execute('SELECT COUNT(*) as c FROM careers').fetchone()['c']
        shlokas   = db.execute('SELECT COUNT(*) as c FROM gyan_kosh').fetchone()['c']
        resources = db.execute('SELECT COUNT(*) as c FROM learning_resources').fetchone()['c']
    except Exception:
        careers = shlokas = resources = 0

    # Get user context
    if session.get('guest'):
        level = session.get('level', 'college')
        goal  = session.get('goal', '')
        user_name = 'Guest'
    else:
        user = get_user(session['user_id'])
        level = user['level']
        goal  = user['goal'] or ''
        user_name = user['username'].title()

    stats = {'careers': careers, 'shlokas': shlokas, 'resources': resources}

    # Daily shloka
    shloka = None
    try:
        shloka = db.execute('SELECT * FROM gyan_kosh ORDER BY RANDOM() LIMIT 1').fetchone()
        if shloka: shloka = dict(shloka)
    except Exception:
        pass

    return render_template('dashboard.html',
                           stats=stats,
                           shloka=shloka,
                           user_name=user_name,
                           goal=goal,
                           school_goals=SCHOOL_GOALS,
                           college_goals=COLLEGE_GOALS,
                           professional_goals=PROFESSIONAL_GOALS)

# ═══════════════════════════════════════════════
#  LANGUAGE TOGGLE
# ═══════════════════════════════════════════════
@app.route('/set-language/<lang>')
def set_language(lang):
    if lang not in LANGUAGES:
        lang = 'en'
    if 'user_id' in session:
        get_db().execute('UPDATE users SET language=? WHERE id=?',
                         (lang, session['user_id']))
        get_db().commit()
    else:
        session['lang'] = lang
    return redirect(request.referrer or url_for('dashboard'))

# ═══════════════════════════════════════════════
#  CAREER MODULE
# ═══════════════════════════════════════════════
@app.route('/career')
@login_required
@onboarding_required
def career_home():
    return render_template('career/quiz.html')

@app.route('/career/quiz', methods=['GET', 'POST'])
@login_required
def career_quiz():
    if request.method == 'POST':
        try:
            data = request.json
            interests = {k: data.get(k, 0)
                         for k in ['technical','creative','social','analytical','entrepreneurial']}
            top2 = sorted(interests.items(), key=lambda x: x[1], reverse=True)[:2]
            cat_map = {'technical':'Technology','creative':'Creative',
                       'social':'Business','analytical':'Technology','entrepreneurial':'Business'}
            db = get_db()
            careers, seen = [], set()
            for interest, _ in top2:
                cat = cat_map.get(interest, 'Technology')
                for row in db.execute('SELECT * FROM careers WHERE category=? LIMIT 3', (cat,)).fetchall():
                    d = dict(row)
                    if d['id'] not in seen:
                        careers.append(d); seen.add(d['id'])
            return jsonify({'success': True, 'careers': careers[:5], 'interests': interests})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return render_template('career/quiz.html')

@app.route('/career/browse')
@login_required
@onboarding_required
def career_browse():
    try:
        db = get_db()
        category = request.args.get('category', 'all')
        if category == 'all':
            careers = db.execute('SELECT * FROM careers ORDER BY title').fetchall()
        else:
            careers = db.execute('SELECT * FROM careers WHERE category=? ORDER BY title',
                                 (category,)).fetchall()
        categories = db.execute('SELECT DISTINCT category FROM careers').fetchall()
        return render_template('career/browse.html',
                               careers=[dict(r) for r in careers],
                               categories=[r['category'] for r in categories],
                               selected_category=category)
    except Exception as e:
        return f'Error: {e}', 500

@app.route('/career/detail/<int:cid>')
@login_required
def career_detail(cid):
    try:
        career = get_db().execute('SELECT * FROM careers WHERE id=?', (cid,)).fetchone()
        if not career:
            return 'Not found', 404
        c = dict(career)
        # map category to emoji icon
        icons = {'Technology':'💻','Business':'📊','Creative':'🎨',
                 'Healthcare':'🩺','Legal':'⚖️','Education':'📚','Science':'🔬'}
        career_icon = icons.get(c.get('category',''), '🎯')
        return render_template('career_detail.html', career=c, career_icon=career_icon)
    except Exception as e:
        return f'Error: {e}', 500

# ═══════════════════════════════════════════════
#  GYAN KOSH
# ═══════════════════════════════════════════════
@app.route('/gyan')
@login_required
@onboarding_required
def gyan_home():
    try:
        shloka = get_db().execute(
            'SELECT * FROM gyan_kosh ORDER BY RANDOM() LIMIT 1').fetchone()
        if shloka:
            return render_template('gyan/daily.html', shloka=dict(shloka))
        return 'No shlokas', 500
    except Exception as e:
        return f'Error: {e}', 500

@app.route('/gyan/search')
@login_required
@onboarding_required
def gyan_search():
    try:
        q = request.args.get('q', '').strip()
        db = get_db()
        if q:
            sp = f'%{q}%'
            shlokas = db.execute('''SELECT * FROM gyan_kosh WHERE
                hindi_meaning LIKE ? OR english_meaning LIKE ?
                OR practical_application LIKE ? OR tags LIKE ?''',
                (sp,sp,sp,sp)).fetchall()
        else:
            shlokas = db.execute(
                'SELECT * FROM gyan_kosh ORDER BY chapter,verse_number LIMIT 20').fetchall()
        return render_template('gyan/search.html',
                               shlokas=[dict(r) for r in shlokas], query=q)
    except Exception as e:
        return f'Error: {e}', 500

@app.route('/gyan/detail/<int:sid>')
@login_required
def gyan_detail(sid):
    try:
        s = get_db().execute('SELECT * FROM gyan_kosh WHERE id=?', (sid,)).fetchone()
        if s:
            return render_template('gyan/detail.html', shloka=dict(s))
        return 'Not found', 404
    except Exception as e:
        return f'Error: {e}', 500

# ═══════════════════════════════════════════════
#  SKILL SAATHI
# ═══════════════════════════════════════════════
@app.route('/skill')
@login_required
@onboarding_required
def skill_home():
    try:
        db = get_db()
        if session.get('guest'):
            lvl = session.get('level','college')
            board = class_std = ''
        else:
            user = get_user(session['user_id'])
            lvl   = user['level']
            board = user['board'] or ''
            class_std = user['class_std'] or ''

        level_info = LEVELS.get(lvl, LEVELS['college'])
        diff_filter = level_info.get('skill_difficulty',
                                     ['Beginner','Intermediate'])
        ph = ','.join(['?']*len(diff_filter))
        resources = db.execute(
            f'SELECT * FROM learning_resources WHERE difficulty IN ({ph}) '
            f'ORDER BY quality_score DESC LIMIT 12', diff_filter).fetchall()
        if not resources:
            resources = db.execute(
                'SELECT * FROM learning_resources ORDER BY quality_score DESC LIMIT 12'
            ).fetchall()
        topics = db.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
        return render_template('skill/browse.html',
                               resources=[dict(r) for r in resources],
                               topics=[r['topic'] for r in topics],
                               selected_topic='all', selected_difficulty='all',
                               free_only=False)
    except Exception as e:
        return f'Error: {e}', 500

@app.route('/skill/browse')
@login_required
@onboarding_required
def skill_browse():
    try:
        db   = get_db()
        topic      = request.args.get('topic', 'all')
        difficulty = request.args.get('difficulty', 'all')
        free_only  = request.args.get('free', 'false') == 'true'
        q, params  = 'SELECT * FROM learning_resources WHERE 1=1', []
        if topic != 'all':
            q += ' AND topic=?'; params.append(topic)
        if difficulty != 'all':
            q += ' AND difficulty=?'; params.append(difficulty)
        if free_only:
            q += ' AND is_free=1'
        q += ' ORDER BY quality_score DESC'
        resources = db.execute(q, params).fetchall()
        topics    = db.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
        return render_template('skill/browse.html',
                               resources=[dict(r) for r in resources],
                               topics=[r['topic'] for r in topics],
                               selected_topic=topic,
                               selected_difficulty=difficulty,
                               free_only=free_only)
    except Exception as e:
        return f'Error: {e}', 500

# ═══════════════════════════════════════════════
#  AI CHATBOT CONFIG
# ═══════════════════════════════════════════════
@app.route('/api/chat-config', methods=['POST'])
@login_required
def chat_config():
    try:
        if session.get('guest'):
            level = session.get('level', 'college')
            goal  = session.get('goal', '')
            class_std = session.get('class_std', '')
            board     = session.get('board', '')
            lang      = session.get('lang', 'en')
            user_name = 'Friend'
        else:
            user = get_user(session['user_id'])
            level     = user['level']
            goal      = user['goal'] or ''
            class_std = user['class_std'] or ''
            board     = user['board'] or ''
            lang      = user['language']
            user_name = user['username'].title()

        li = LEVELS.get(level, LEVELS['college'])
        lang_instruction = (
            'Respond in natural Hinglish (mix Hindi + English like a dost). '
            'Use Devanagari script for Hindi words. '
            'Be warm, use "bhai/yaar/dost" naturally.'
            if lang == 'hi' else
            'Respond in clear, friendly English. Be warm and encouraging.'
        )

        context = f'Level: {li["label"]}'
        if class_std: context += f', Class {class_std}'
        if board:     context += f', Board: {board}'
        if goal:      context += f', Goal: {goal}'

        system = f"""You are Marg Darshak AI Guru 🧭, a brilliant and caring guide for Indian students.

User: {user_name} | {context}

{lang_instruction}

Your role:
- Give personalized career guidance, Bhagavad Gita wisdom, study tips, skill advice
- Always tailor advice to the user's specific level, class, board, and goal
- When quoting Gita, give Sanskrit shloka + meaning + modern application
- Be specific: mention real exams (JEE/NEET/UPSC), real colleges (IIT/AIIMS), real resources
- Keep responses concise but impactful (2–4 paragraphs max)
- Use emojis naturally 🙏✨

End every response with one short encouraging line."""

        return jsonify({'success': True, 'system': system})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════
#  AI GOAL PREDICTION (school)
# ═══════════════════════════════════════════════
@app.route('/api/predict-goal', methods=['POST'])
@login_required
def predict_goal():
    """Returns AI-generated roadmap based on current class + board + goal"""
    try:
        data      = request.json
        goal_key  = data.get('goal', '')
        class_std = data.get('class_std', '10')
        board     = data.get('board', 'CBSE')

        goal_info = SCHOOL_GOALS.get(goal_key)
        if not goal_info:
            return jsonify({'success': False, 'error': 'Unknown goal'}), 400

        years_left = max(0, 12 - int(class_std)) if class_std.isdigit() else 2

        roadmap = {
            'goal': goal_info['label'],
            'icon': goal_info['icon'],
            'exam': goal_info['exam'],
            'path': goal_info['path'],
            'subjects': goal_info['subjects'],
            'years_left': years_left,
            'board': board,
            'milestones': _build_milestones(goal_key, int(class_std) if class_std.isdigit() else 10, board),
        }
        return jsonify({'success': True, 'roadmap': roadmap})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def _build_milestones(goal, cls, board):
    base = []
    if goal == 'doctor':
        if cls <= 9:  base.append({'class':'9-10','task':'Focus on Science & Maths. Score 85%+ in boards.'})
        if cls <= 11: base.append({'class':'11-12','task':'Take PCB stream. Start NCERT Biology deep study.'})
        base += [
            {'class':'12','task':f'Appear in {board} boards. Target 90%+.'},
            {'class':'12','task':'Register for NEET. Join a coaching or use NTA Abhyas app.'},
            {'class':'After 12','task':'Clear NEET → MBBS in Govt Medical College (AIIMS/State).'},
        ]
    elif goal == 'engineer':
        if cls <= 9:  base.append({'class':'9-10','task':'Build strong Maths & Science base. Practice NCERT thoroughly.'})
        if cls <= 11: base.append({'class':'11-12','task':'Take PCM stream. Focus on Physics, Chemistry, Maths.'})
        base += [
            {'class':'11-12','task':'Join JEE coaching / use PW / Unacademy. Solve DPPs daily.'},
            {'class':'12','task':f'{board} boards + JEE Mains & Advanced preparation.'},
            {'class':'After 12','task':'Clear JEE → IIT / NIT / IIIT. Alternate: BITSAT, state CETs.'},
        ]
    elif goal == 'ias':
        base += [
            {'class':f'{cls}-12','task':'Read newspaper daily (The Hindu/IE). Build general awareness.'},
            {'class':'After 12','task':'Choose graduation wisely (History/Polity/Economics helps).'},
            {'class':'Graduation','task':'Start UPSC prep in final year. Join test series.'},
            {'class':'Post Grad','task':'Appear in UPSC CSE. 3 attempts average. Stay consistent.'},
        ]
    else:
        base += [
            {'class':f'{cls}','task':f'Focus on subjects: {", ".join(SCHOOL_GOALS[goal]["subjects"][:2])}.'},
            {'class':'11-12','task':f'Choose right stream. Target exam: {SCHOOL_GOALS[goal]["exam"]}.'},
            {'class':'After 12','task':f'Path: {SCHOOL_GOALS[goal]["path"]}'},
        ]
    return base

# ═══════════════════════════════════════════════
#  API
# ═══════════════════════════════════════════════
@app.route('/api/stats')
def api_stats():
    try:
        db = get_db()
        return jsonify({
            'careers':   db.execute('SELECT COUNT(*) as c FROM careers').fetchone()['c'],
            'shlokas':   db.execute('SELECT COUNT(*) as c FROM gyan_kosh').fetchone()['c'],
            'resources': db.execute('SELECT COUNT(*) as c FROM learning_resources').fetchone()['c'],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ═══════════════════════════════════════════════
#  INTEREST QUIZ
# ═══════════════════════════════════════════════
@app.route('/career/interest-quiz')
@login_required
@onboarding_required
def interest_quiz():
    return render_template('interest_quiz.html')

@app.route('/api/save-quiz-result', methods=['POST'])
@login_required
def save_quiz_result():
    try:
        data = request.json
        if session.get('guest'):
            return jsonify({'success': True})
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, holland_code TEXT, scores TEXT,
            top_careers TEXT, taken_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute(
            'INSERT INTO quiz_results(user_id,holland_code,scores,top_careers) VALUES(?,?,?,?)',
            (session['user_id'],
             data.get('holland_code',''),
             json.dumps(data.get('scores',{})),
             json.dumps(data.get('top_careers',[])))
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════
#  GRANTH KOSH (Scriptures)
# ═══════════════════════════════════════════════
@app.route('/granth')
@login_required
@onboarding_required
def granth_kosh():
    return render_template('granth_kosh.html')

# ═══════════════════════════════════════════════
#  RESOURCES EXPLORER
# ═══════════════════════════════════════════════
@app.route('/resources')
@login_required
@onboarding_required
def resources_explorer():
    return render_template('resources_explorer.html')

# ═══════════════════════════════════════════════
#  SCHOOL RESOURCES
# ═══════════════════════════════════════════════
@app.route('/school/resources')
@login_required
@onboarding_required
def school_resources():
    if session.get('guest'):
        user_class = session.get('class_std', '9')
        user_board = session.get('board', 'CBSE')
    else:
        user = get_user(session['user_id'])
        user_class = user['class_std'] or '9'
        user_board = user['board'] or 'CBSE'

    boards = ['CBSE', 'ICSE', 'State Board', 'IB', 'NIOS']
    return render_template('school_resources.html',
                           user_class=user_class,
                           user_board=user_board,
                           boards=boards)

# ═══════════════════════════════════════════════
#  PROGRESS TRACKER
# ═══════════════════════════════════════════════
@app.route('/api/save-progress', methods=['POST'])
@login_required
def save_progress():
    try:
        data     = request.json
        subject  = data.get('subject','')
        class_std = data.get('class_std','')
        progress = int(data.get('progress', 0))

        if session.get('guest'):
            return jsonify({'success': True, 'note': 'guest mode, not persisted'})

        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, subject TEXT, class_std TEXT,
            progress INTEGER DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, subject, class_std)
        )''')
        db.execute('''INSERT INTO user_progress(user_id,subject,class_std,progress,updated_at)
            VALUES(?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(user_id,subject,class_std) DO UPDATE SET progress=excluded.progress,
            updated_at=CURRENT_TIMESTAMP''',
            (session['user_id'], subject, class_std, progress))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-progress')
@login_required
def get_progress():
    try:
        if session.get('guest'):
            return jsonify({'success': True, 'progress': {}})
        db = get_db()
        rows = db.execute(
            'SELECT subject, class_std, progress FROM user_progress WHERE user_id=?',
            (session['user_id'],)).fetchall()
        result = {f"{r['class_std']}_{r['subject']}": r['progress'] for r in rows}
        return jsonify({'success': True, 'progress': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════
#  SAVE CAREER
# ═══════════════════════════════════════════════
@app.route('/api/save-career', methods=['POST'])
@login_required
def save_career_api():
    try:
        data      = request.json
        career_id = int(data.get('career_id', 0))

        if session.get('guest'):
            return jsonify({'success': True, 'note': 'guest mode'})

        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS saved_careers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, career_id INTEGER, saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, career_id)
        )''')
        db.execute('''INSERT OR IGNORE INTO saved_careers(user_id, career_id) VALUES(?,?)''',
                   (session['user_id'], career_id))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/saved-careers')
@login_required
def get_saved_careers():
    try:
        if session.get('guest'):
            return jsonify({'success': True, 'careers': []})
        db = get_db()
        rows = db.execute('''SELECT c.* FROM careers c
            JOIN saved_careers sc ON sc.career_id = c.id
            WHERE sc.user_id=? ORDER BY sc.saved_at DESC''',
            (session['user_id'],)).fetchall()
        return jsonify({'success': True, 'careers': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════
#  INTEREST QUIZ
# ═══════════════════════════════════════════════
@app.route('/quiz')
@login_required
@onboarding_required
def quiz():
    try:
        db = get_db()
        careers = db.execute('SELECT * FROM careers ORDER BY title').fetchall()
        return render_template('quiz.html', careers=[dict(c) for c in careers])
    except Exception as e:
        return f'Error: {e}', 500



# ═══════════════════════════════════════════════
#  SCRIPTURE
# ═══════════════════════════════════════════════
@app.route('/scripture')
@login_required
@onboarding_required
def scripture():
    try:
        db = get_db()
        shlokas = db.execute('SELECT * FROM gyan_kosh ORDER BY chapter,verse_number').fetchall()
        return render_template('scripture.html', shlokas=[dict(s) for s in shlokas])
    except Exception as e:
        return f'Error: {e}', 500




# ═══════════════════════════════════════════════
#  AI RECOMMENDATION
# ═══════════════════════════════════════════════
@app.route('/ai-recommendation')
@login_required
@onboarding_required
def ai_recommendation():
    try:
        quiz_result = None
        if not session.get('guest'):
            db = get_db()
            row = db.execute(
                'SELECT * FROM quiz_results WHERE user_id=? ORDER BY taken_at DESC LIMIT 1',
                (session['user_id'],)
            ).fetchone()
            if row:
                qr = dict(row)
                # Parse top_careers JSON
                try:
                    tc = json.loads(qr.get('top_careers','[]'))
                except:
                    tc = []
                qr['top_careers_list'] = tc
                quiz_result = qr
        return render_template('ai_recommendation.html', quiz_result=quiz_result)
    except Exception as e:
        return f'Error: {e}', 500

@app.route('/api/save-recommendation', methods=['POST'])
@login_required
def save_recommendation():
    try:
        if session.get('guest'):
            return jsonify({'success': True})
        data = request.json
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS ai_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, recommendation TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute(
            'INSERT INTO ai_recommendations(user_id, recommendation) VALUES(?,?)',
            (session['user_id'], data.get('recommendation',''))
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════
#  PROGRESS DASHBOARD
# ═══════════════════════════════════════════════
@app.route('/progress')
@login_required
@onboarding_required
def progress_dashboard():
    try:
        quiz_result = None
        if not session.get('guest'):
            db = get_db()
            row = db.execute(
                'SELECT * FROM quiz_results WHERE user_id=? ORDER BY taken_at DESC LIMIT 1',
                (session['user_id'],)
            ).fetchone()
            if row:
                qr = dict(row)
                quiz_result = qr
        return render_template('progress_dashboard.html', quiz_result=quiz_result)
    except Exception as e:
        return f'Error: {e}', 500

# ═══════════════════════════════════════════════
#  MOCK TEST
# ═══════════════════════════════════════════════
@app.route('/mock-test')
@login_required
@onboarding_required
def mock_test():
    return render_template('mock_test.html')

@app.route('/api/save-test-result', methods=['POST'])
@login_required
def save_test_result():
    try:
        if session.get('guest'):
            return jsonify({'success': True})
        data = request.json
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, subject TEXT, score INTEGER,
            correct INTEGER, wrong INTEGER, skipped INTEGER,
            total INTEGER, time_taken INTEGER,
            taken_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute(
            '''INSERT INTO test_results
               (user_id,subject,score,correct,wrong,skipped,total,time_taken)
               VALUES(?,?,?,?,?,?,?,?)''',
            (session['user_id'], data.get('subject',''),
             data.get('score',0), data.get('correct',0),
             data.get('wrong',0), data.get('skipped',0),
             data.get('total',0), data.get('time_taken',0))
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════
#  ERROR HANDLERS
# ═══════════════════════════════════════════════
@app.errorhandler(404)
def not_found(e): return render_template('404.html'), 404
@app.errorhandler(500)
def server_error(e): return render_template('500.html'), 500

# ═══════════════════════════════════════════════
#  BOOT
# ═══════════════════════════════════════════════
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)