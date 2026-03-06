import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, jsonify, session, g)
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'database', 'marg_darshak.db')

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# ─────────────────────────────────────────────
#  DB HELPERS
# ─────────────────────────────────────────────
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, '_database', None)
    if db: db.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email    TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        level    TEXT DEFAULT 'school',
        goal     TEXT DEFAULT '',
        class_std TEXT DEFAULT '',
        board     TEXT DEFAULT '',
        stream    TEXT DEFAULT '',
        experience TEXT DEFAULT '',
        domain    TEXT DEFAULT '',
        language  TEXT DEFAULT 'en',
        onboarded INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS careers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, category TEXT, description TEXT,
        roadmap TEXT, skills TEXT, colleges TEXT,
        avg_salary_inr INTEGER, growth_rate TEXT,
        difficulty TEXT, education TEXT, job_roles TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS gyan_kosh (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT DEFAULT 'gita',
        chapter INTEGER, verse_number INTEGER,
        sanskrit TEXT, hindi_meaning TEXT,
        english_meaning TEXT, practical_application TEXT, tags TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS learning_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT, title TEXT, url TEXT,
        platform TEXT, difficulty TEXT,
        is_free INTEGER DEFAULT 1, quality_score REAL DEFAULT 4.0,
        subject TEXT, level TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS saved_careers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, career_id INTEGER, saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, career_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, holland_code TEXT, scores TEXT,
        top_careers TEXT, taken_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, subject TEXT, score INTEGER,
        correct INTEGER, wrong INTEGER, skipped INTEGER,
        total INTEGER, time_taken INTEGER,
        taken_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, subject TEXT, class_std TEXT,
        progress INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, subject, class_std)
    )''')

    # Seed careers if empty
    if not conn.execute('SELECT id FROM careers LIMIT 1').fetchone():
        careers = [
            ('Software Engineer','Technology',
             'Build software products used by millions. India\'s most in-demand career.',
             'Learn programming basics→DSA→Projects→Internship→Job',
             'Python;JavaScript;DSA;System Design;Git',
             'IIT;NIT;BITS;VIT;DTU',
             1200000,'35%','Medium','B.Tech/BE Computer Science','Backend Dev;Frontend Dev;Full Stack;DevOps'),
            ('Doctor (MBBS)','Healthcare',
             'Diagnose and treat patients. One of the most respected professions in India.',
             'Class 11 PCB→NEET preparation→MBBS→Internship→MD/MS',
             'Biology;Chemistry;Clinical Skills;Patient Communication',
             'AIIMS;JIPMER;CMC Vellore;MAMC;GMC',
             800000,'25%','High','MBBS (5.5 yrs)','General Physician;Specialist;Surgeon;Researcher'),
            ('IAS Officer','Government',
             'Lead India\'s administrative machinery. Shape policy for 1.4 billion people.',
             'Graduation→UPSC Prelims→Mains→Interview→Training',
             'GK;Current Affairs;Essay Writing;Leadership;Management',
             'Any top University',
             1400000,'Stable','Very High','Any Graduation','DM;SDM;Secretary;Ambassador'),
            ('CA (Chartered Accountant)','Finance',
             'India\'s most respected finance professional. High demand in every sector.',
             'Class 12 Commerce→CA Foundation→Intermediate→Final',
             'Accountancy;Taxation;Audit;Finance;Law',
             'ICAI (national body)',
             1500000,'20%','High','CA Program (4-5 yrs)','Auditor;Tax Consultant;CFO;Finance Manager'),
            ('Data Scientist','Technology',
             'Extract insights from data using AI/ML. Fastest growing field globally.',
             'Maths/Stats foundation→Python→ML algorithms→Projects→Job',
             'Python;Statistics;Machine Learning;SQL;Tableau',
             'IIT;IISc;BITS;NIT;Top private colleges',
             1800000,'45%','Medium-High','B.Tech/B.Sc + ML courses','ML Engineer;Data Analyst;AI Researcher;BI Analyst'),
            ('Lawyer','Legal',
             'Advocate for justice in courts and boardrooms across India.',
             'Class 12→CLAT→LLB (5yr integrated) or BA+LLB→Practice',
             'Legal Research;Argumentation;Contract Drafting;Criminal Law;Corporate Law',
             'NLU Delhi;NLSIU;NALSAR;Symbiosis Law',
             900000,'18%','High','LLB / BA LLB / BBA LLB','Advocate;Corporate Lawyer;Judge;Legal Advisor'),
            ('Architect','Design',
             'Design buildings and spaces that shape how people live and work.',
             'Class 12 PCM→NATA→B.Arch (5yr)→Internship→Practice',
             'AutoCAD;3D Modelling;Design Thinking;Structural Knowledge',
             'SPA Delhi;CEPT;IIT Roorkee;JNAFAU',
             900000,'15%','High','B.Arch (5 yrs)','Building Architect;Interior Designer;Urban Planner'),
            ('Entrepreneur','Business',
             'Build companies from scratch. Create jobs and solve real problems.',
             'Learn a skill→Identify problem→Build MVP→Get users→Scale',
             'Business Development;Sales;Product Thinking;Leadership;Finance',
             'IIM;ISB;IIT;Or skip college entirely',
             0,'Unlimited','Very High','Any / MBA preferred','Founder;CEO;Business Owner'),
            ('UI/UX Designer','Design',
             'Create digital products people love to use. Combines art and psychology.',
             'Learn design tools→Portfolio→Freelance/Internship→Full-time',
             'Figma;User Research;Prototyping;Visual Design;HTML/CSS',
             'NID;NIFT;MIT Institute of Design;Symbiosis',
             1100000,'40%','Medium','BDes/MDes or self-taught','Product Designer;UX Researcher;Design Lead'),
            ('Research Scientist','Science',
             'Push the boundaries of human knowledge through research and experiments.',
             'Strong academics→IIT/IISc/IISER→PhD→Post-doc→Research Position',
             'Research Methodology;Data Analysis;Scientific Writing;Domain Expertise',
             'IISc;IIT;IISER;TIFR;CSIR Labs',
             800000,'20%','Very High','PhD required','Research Scientist;Professor;R&D Lead'),
        ]
        conn.executemany(
            '''INSERT INTO careers(title,category,description,roadmap,skills,colleges,
               avg_salary_inr,growth_rate,difficulty,education,job_roles) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
            careers)

    # Seed shlokas if empty
    if not conn.execute('SELECT id FROM gyan_kosh LIMIT 1').fetchone():
        shlokas = [
            ('gita',2,47,
             'कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।',
             'You have the right to perform your duties, but never to the results.',
             'Focus only on your work — exams, job applications, projects. Results will follow.',
             'karma,work,focus'),
            ('gita',6,5,
             'उद्धरेदात्मनात्मानं नात्मानमवसादयेत्।',
             'Elevate yourself through your own effort; do not degrade yourself.',
             'No one else will build your career for you. Self-discipline is the only superpower.',
             'self,discipline,growth'),
            ('gita',3,27,
             'प्रकृतेः क्रियमाणानि गुणैः कर्माणि सर्वशः।',
             'All actions are performed by nature\'s qualities; the ego-deluded think "I am the doer."',
             'Stay humble in success. Great teams and leaders understand collective effort.',
             'ego,humility,leadership'),
            ('gita',18,46,
             'स्वकर्मणा तमभ्यर्च्य सिद्धिं विन्दति मानवः।',
             'A person attains perfection by worshipping through their own natural work.',
             'Choose a career aligned with your natural strengths — that is where excellence lives.',
             'purpose,career,dharma'),
            ('gita',2,14,
             'मात्रास्पर्शास्तु कौन्तेय शीतोष्णसुखदुःखदाः।',
             'Contacts of senses with objects give rise to cold/heat, pleasure/pain. Endure them.',
             'Exam failure, job rejection — these are temporary. Resilience defines your career.',
             'resilience,stress,mindset'),
            ('chanakya',1,1,
             'काक चेष्टा, बको ध्यानम्, श्वान निद्रा तथैव च।',
             'Effort of a crow, focus of a heron, light sleep of a dog — these mark a true student.',
             'Serious study demands serious sacrifice. Eliminate distractions ruthlessly.',
             'focus,study,discipline'),
            ('upanishad',1,1,
             'तत्त्वमसि — Tat Tvam Asi',
             'That art Thou — you are the infinite, boundless potential itself.',
             'Your biggest limitations are self-imposed beliefs. You are capable of far more.',
             'mindset,potential,self'),
            ('vedas',1,1,
             'आ नो भद्राः क्रतवो यन्तु विश्वतः',
             'Let noble thoughts come to us from all directions.',
             'Learn from every source — books, mentors, failures, nature. Wisdom is everywhere.',
             'learning,knowledge,wisdom'),
        ]
        conn.executemany(
            '''INSERT INTO gyan_kosh(source,chapter,verse_number,sanskrit,
               english_meaning,practical_application,tags) VALUES(?,?,?,?,?,?,?)''',
            shlokas)

    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
#  AUTH HELPERS
# ─────────────────────────────────────────────
def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()

def get_user(uid):
    row = get_db().execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    return dict(row) if row else None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

def onboarding_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' in session and not session.get('guest'):
            user = get_user(session['user_id'])
            if user and not user.get('onboarded'):
                return redirect(url_for('onboarding'))
        return f(*args, **kwargs)
    return decorated

def inject_user():
    """Returns current user dict or None — used in templates via g"""
    if 'user_id' in session and not session.get('guest'):
        return get_user(session['user_id'])
    return None

@app.context_processor
def inject_globals():
    user = inject_user()
    return dict(
        current_user=user,
        level=user['level'] if user else session.get('level','school'),
        lang=user['language'] if user else session.get('lang','en'),
        is_authenticated='user_id' in session,
        is_guest=session.get('guest', False),
    )

# ─────────────────────────────────────────────
#  AUTH ROUTES
# ─────────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        data = request.json or request.form
        identifier = data.get('identifier','').strip()
        password   = data.get('password','').strip()
        if not identifier or not password:
            return jsonify({'success':False,'error':'Please fill all fields.'}), 400
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE email=? OR username=?',
            (identifier, identifier)
        ).fetchone()
        if not user or dict(user)['password'] != hash_password(password):
            return jsonify({'success':False,'error':'Invalid credentials. Please try again.'}), 401
        u = dict(user)
        session.clear()
        session['user_id'] = u['id']
        session.permanent = True
        return jsonify({'success':True,'redirect': url_for('dashboard')})
    return render_template('auth.html', mode='login')

@app.route('/register', methods=['GET','POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        data     = request.json or request.form
        username = data.get('username','').strip()
        email    = data.get('email','').strip()
        password = data.get('password','').strip()
        if not all([username, email, password]):
            return jsonify({'success':False,'error':'All fields are required.'}), 400
        if len(password) < 6:
            return jsonify({'success':False,'error':'Password must be at least 6 characters.'}), 400
        db = get_db()
        if db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone():
            return jsonify({'success':False,'error':'This email is already registered.'}), 409
        if db.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone():
            return jsonify({'success':False,'error':'This username is taken.'}), 409
        db.execute(
            'INSERT INTO users(username,email,password) VALUES(?,?,?)',
            (username, email, hash_password(password))
        )
        db.commit()
        user = db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        session.clear()
        session['user_id'] = dict(user)['id']
        session.permanent = True
        return jsonify({'success':True,'redirect': url_for('onboarding')})
    return render_template('auth.html', mode='register')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/guest')
def guest_login():
    session.clear()
    session['guest']    = True
    session['user_id']  = 0
    session['level']    = 'school'
    session['lang']     = 'en'
    return redirect(url_for('dashboard'))

# ─────────────────────────────────────────────
#  ONBOARDING
# ─────────────────────────────────────────────
@app.route('/onboarding', methods=['GET','POST'])
@login_required
def onboarding():
    if request.method == 'POST':
        data = request.json or request.form
        if session.get('guest'):
            session['level'] = data.get('level','school')
            return jsonify({'success':True,'redirect': url_for('dashboard')})
        db = get_db()
        db.execute('''UPDATE users SET
            level=?, goal=?, class_std=?, board=?,
            stream=?, experience=?, domain=?, language=?, onboarded=1
            WHERE id=?''', (
            data.get('level','school'),
            data.get('goal',''),
            data.get('class_std',''),
            data.get('board',''),
            data.get('stream',''),
            data.get('experience',''),
            data.get('domain',''),
            data.get('language','en'),
            session['user_id']
        ))
        db.commit()
        return jsonify({'success':True,'redirect': url_for('dashboard')})
    return render_template('onboarding.html')

# ─────────────────────────────────────────────
#  MAIN PAGES
# ─────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
@onboarding_required
def dashboard():
    db = get_db()
    user = inject_user()
    career_count   = db.execute('SELECT COUNT(*) FROM careers').fetchone()[0]
    shloka_count   = db.execute('SELECT COUNT(*) FROM gyan_kosh').fetchone()[0]
    resource_count = db.execute('SELECT COUNT(*) FROM learning_resources').fetchone()[0]
    daily_shloka   = db.execute(
        'SELECT * FROM gyan_kosh ORDER BY RANDOM() LIMIT 1'
    ).fetchone()
    saved_count = 0
    quiz_result = None
    if user:
        saved_count = db.execute(
            'SELECT COUNT(*) FROM saved_careers WHERE user_id=?',(user['id'],)
        ).fetchone()[0]
        row = db.execute(
            'SELECT * FROM quiz_results WHERE user_id=? ORDER BY taken_at DESC LIMIT 1',
            (user['id'],)
        ).fetchone()
        if row: quiz_result = dict(row)
    return render_template('dashboard.html',
        career_count=career_count, shloka_count=shloka_count,
        resource_count=resource_count,
        daily_shloka=dict(daily_shloka) if daily_shloka else None,
        saved_count=saved_count, quiz_result=quiz_result)

# ─────────────────────────────────────────────
#  CAREERS
# ─────────────────────────────────────────────
@app.route('/career')
@login_required
@onboarding_required
def career_home():
    return render_template('career/quiz.html')

@app.route('/career/browse')
@login_required
@onboarding_required
def career_browse():
    db = get_db()
    category = request.args.get('category','')
    search   = request.args.get('q','')
    query = 'SELECT * FROM careers'
    params = []
    if category:
        query += ' WHERE category=?'; params.append(category)
    elif search:
        query += ' WHERE title LIKE ? OR description LIKE ?'
        params += [f'%{search}%', f'%{search}%']
    careers    = [dict(r) for r in db.execute(query, params).fetchall()]
    categories = [r[0] for r in db.execute('SELECT DISTINCT category FROM careers').fetchall()]
    user = inject_user()
    saved_ids = []
    if user:
        saved_ids = [r[0] for r in db.execute(
            'SELECT career_id FROM saved_careers WHERE user_id=?',(user['id'],)
        ).fetchall()]
    return render_template('career/browse.html',
        careers=careers, categories=categories,
        saved_ids=saved_ids, current_category=category, search=search)

@app.route('/career/detail/<int:cid>')
@login_required
@onboarding_required
def career_detail(cid):
    db = get_db()
    row = db.execute('SELECT * FROM careers WHERE id=?',(cid,)).fetchone()
    if not row: return redirect(url_for('career_browse'))
    career = dict(row)
    icon_map = {'Technology':'💻','Healthcare':'🩺','Government':'🏛️',
                'Finance':'📊','Design':'🎨','Legal':'⚖️',
                'Science':'🔬','Business':'🚀','Education':'📚'}
    career['icon'] = icon_map.get(career.get('category',''),'🎯')
    user = inject_user()
    is_saved = False
    if user:
        is_saved = bool(db.execute(
            'SELECT id FROM saved_careers WHERE user_id=? AND career_id=?',
            (user['id'], cid)
        ).fetchone())
    return render_template('career/detail.html', career=career, is_saved=is_saved)

# ─────────────────────────────────────────────
#  GYAN KOSH
# ─────────────────────────────────────────────
@app.route('/gyan')
@login_required
@onboarding_required
def gyan_home():
    db = get_db()
    daily = db.execute('SELECT * FROM gyan_kosh ORDER BY RANDOM() LIMIT 1').fetchone()
    all_shlokas = [dict(r) for r in db.execute('SELECT * FROM gyan_kosh').fetchall()]
    return render_template('gyan/home.html',
        daily=dict(daily) if daily else None, shlokas=all_shlokas)

# ─────────────────────────────────────────────
#  RESOURCES
# ─────────────────────────────────────────────
@app.route('/skill')
@login_required
@onboarding_required
def skill_home():
    db = get_db()
    resources = [dict(r) for r in db.execute(
        'SELECT * FROM learning_resources ORDER BY quality_score DESC'
    ).fetchall()]
    return render_template('skill/home.html', resources=resources)

# ─────────────────────────────────────────────
#  AI CHATBOT — server side API call
# ─────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Server-side Claude API call — no CORS issues, API key never exposed"""
    try:
        import urllib.request
        data     = request.json
        messages = data.get('messages', [])
        user     = inject_user()

        # Build system prompt from user profile
        if user:
            profile = (f"User: {user['username']} | Level: {user['level']}"
                      + (f" | Class {user['class_std']}" if user.get('class_std') else '')
                      + (f" | Board: {user['board']}" if user.get('board') else '')
                      + (f" | Goal: {user['goal']}" if user.get('goal') else ''))
            lang_note = ('Use Hinglish naturally (mix Hindi+English).'
                        if user.get('language') == 'hi'
                        else 'Respond in clear, friendly English.')
        else:
            profile  = 'Guest user exploring career options.'
            lang_note = 'Respond in clear, friendly English.'

        system = f"""You are Marg Darshak AI Guru 🧭 — a brilliant, caring career guide for Indian students.

{profile}

{lang_note}

Your role:
- Give personalized career guidance tailored to the user's level, class, board, and goal
- Mention real Indian exams (JEE, NEET, UPSC, CLAT, CA), real colleges (IIT, AIIMS, NLU, IIM)
- Quote relevant Bhagavad Gita wisdom when appropriate (Sanskrit + meaning + application)
- Be warm, specific, and actionable — 2-4 paragraphs max
- Use emojis naturally

End every response with one short, encouraging line."""

        payload = json.dumps({
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': 1000,
            'system': system,
            'messages': messages
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())

        text = result['content'][0]['text'] if result.get('content') else 'Sorry, try again.'
        return jsonify({'success': True, 'message': text})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai-recommend', methods=['POST'])
@login_required
def ai_recommend():
    """Server-side AI career recommendation"""
    try:
        import urllib.request
        user = inject_user()
        data = request.json or {}

        profile_parts = []
        if user:
            profile_parts.append(f"Name: {user['username']}")
            profile_parts.append(f"Level: {user['level']}")
            if user.get('class_std'): profile_parts.append(f"Class: {user['class_std']}")
            if user.get('board'):     profile_parts.append(f"Board: {user['board']}")
            if user.get('stream'):    profile_parts.append(f"Stream: {user['stream']}")
            if user.get('goal'):      profile_parts.append(f"Goal: {user['goal'].replace('_',' ')}")
        if data.get('holland_code'):
            profile_parts.append(f"Holland Code (RIASEC): {data['holland_code']}")
        if data.get('top_careers'):
            profile_parts.append(f"Quiz matches: {', '.join(data['top_careers'])}")

        profile_str = '\n'.join(profile_parts) or 'Student exploring career options.'
        lang_note = ('Respond in Hinglish (natural Hindi+English mix).'
                    if (user and user.get('language') == 'hi') else
                    'Respond in clear English.')

        prompt = f"""You are Marg Darshak AI Guru — an expert career counsellor for Indian students.

{lang_note}

Student Profile:
{profile_str}

Write a PERSONALIZED career recommendation with these exact sections (use ### headings):

### 🎯 Your Best Career Matches
(2-3 careers that fit this specific profile, with clear reason for each)

### 🗺 6-Month Action Plan
(Concrete month-by-month steps. Mention real exams, resources like PW/NCERT/Unacademy, deadlines)

### 📚 Must-Learn Skills
(5-6 specific skills + how to learn each one free in India)

### 🏆 Top Colleges & Paths
(Real Indian colleges/paths with entrance exams for their goal)

### ⚡ Wisdom for Your Journey
(One Bhagavad Gita shloka — Sanskrit + meaning + how it applies to their specific situation)

Be SPECIFIC to their profile. Total: 500-700 words. Use **bold** for key terms.
End with an encouraging line addressed to them by name."""

        payload = json.dumps({
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': 1500,
            'messages': [{'role':'user','content': prompt}]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            result = json.loads(resp.read())

        text = result['content'][0]['text'] if result.get('content') else 'Sorry, try again.'

        # Save to DB
        if user:
            db = get_db()
            db.execute('''CREATE TABLE IF NOT EXISTS ai_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, recommendation TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            db.execute('INSERT INTO ai_recommendations(user_id,recommendation) VALUES(?,?)',
                       (user['id'], text))
            db.commit()

        return jsonify({'success': True, 'recommendation': text})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ─────────────────────────────────────────────
#  SAVE / PROGRESS APIS
# ─────────────────────────────────────────────
@app.route('/api/save-career', methods=['POST'])
@login_required
def save_career():
    try:
        if session.get('guest'):
            return jsonify({'success':True})
        data = request.json
        db   = get_db()
        db.execute('INSERT OR IGNORE INTO saved_careers(user_id,career_id) VALUES(?,?)',
                   (session['user_id'], data.get('career_id')))
        db.commit()
        return jsonify({'success':True})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)}), 500

@app.route('/api/unsave-career', methods=['POST'])
@login_required
def unsave_career():
    try:
        if session.get('guest'):
            return jsonify({'success':True})
        data = request.json
        db   = get_db()
        db.execute('DELETE FROM saved_careers WHERE user_id=? AND career_id=?',
                   (session['user_id'], data.get('career_id')))
        db.commit()
        return jsonify({'success':True})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)}), 500

@app.route('/api/save-quiz', methods=['POST'])
@login_required
def save_quiz():
    try:
        if session.get('guest'):
            return jsonify({'success':True})
        data = request.json
        db   = get_db()
        db.execute(
            'INSERT INTO quiz_results(user_id,holland_code,scores,top_careers) VALUES(?,?,?,?)',
            (session['user_id'],
             data.get('holland_code',''),
             json.dumps(data.get('scores',{})),
             json.dumps(data.get('top_careers',[])))
        )
        db.commit()
        return jsonify({'success':True})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)}), 500

@app.route('/api/save-test', methods=['POST'])
@login_required
def save_test():
    try:
        if session.get('guest'):
            return jsonify({'success':True})
        data = request.json
        db   = get_db()
        db.execute('''INSERT INTO test_results
            (user_id,subject,score,correct,wrong,skipped,total,time_taken)
            VALUES(?,?,?,?,?,?,?,?)''',
            (session['user_id'], data.get('subject',''),
             data.get('score',0), data.get('correct',0),
             data.get('wrong',0), data.get('skipped',0),
             data.get('total',0), data.get('time_taken',0)))
        db.commit()
        return jsonify({'success':True})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)}), 500

@app.route('/api/save-progress', methods=['POST'])
@login_required
def save_progress():
    try:
        if session.get('guest'):
            return jsonify({'success':True})
        data = request.json
        db   = get_db()
        db.execute('''INSERT INTO user_progress(user_id,subject,class_std,progress)
            VALUES(?,?,?,?)
            ON CONFLICT(user_id,subject,class_std) DO UPDATE SET
            progress=excluded.progress, updated_at=CURRENT_TIMESTAMP''',
            (session['user_id'], data.get('subject',''),
             data.get('class_std',''), data.get('progress',0)))
        db.commit()
        return jsonify({'success':True})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)}), 500

@app.route('/api/get-progress')
@login_required
def get_progress():
    try:
        if session.get('guest'):
            return jsonify({'success':True,'progress':{}})
        db   = get_db()
        rows = db.execute(
            'SELECT subject, class_std, progress FROM user_progress WHERE user_id=?',
            (session['user_id'],)
        ).fetchall()
        return jsonify({'success':True,
            'progress':{f"{r['class_std']}_{r['subject']}":r['progress'] for r in rows}})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)}), 500

@app.route('/api/stats')
def api_stats():
    db = get_db()
    return jsonify({
        'careers':   db.execute('SELECT COUNT(*) FROM careers').fetchone()[0],
        'shlokas':   db.execute('SELECT COUNT(*) FROM gyan_kosh').fetchone()[0],
        'resources': db.execute('SELECT COUNT(*) FROM learning_resources').fetchone()[0],
        'users':     db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
    })

# ─────────────────────────────────────────────
#  NEW FEATURE PAGES
# ─────────────────────────────────────────────
@app.route('/granth')
@login_required
@onboarding_required
def granth_kosh():
    return render_template('granth.html')

@app.route('/resources')
@login_required
@onboarding_required
def resources_explorer():
    return render_template('resources.html')

@app.route('/career/interest-quiz')
@login_required
@onboarding_required
def interest_quiz():
    return render_template('career/interest_quiz.html')

@app.route('/ai-recommendation')
@login_required
@onboarding_required
def ai_recommendation():
    db = get_db()
    quiz_result = None
    user = inject_user()
    if user:
        row = db.execute(
            'SELECT * FROM quiz_results WHERE user_id=? ORDER BY taken_at DESC LIMIT 1',
            (user['id'],)
        ).fetchone()
        if row:
            qr = dict(row)
            try: qr['top_careers_list'] = json.loads(qr.get('top_careers','[]'))
            except: qr['top_careers_list'] = []
            quiz_result = qr
    return render_template('ai_recommend.html', quiz_result=quiz_result)

@app.route('/mock-test')
@login_required
@onboarding_required
def mock_test():
    return render_template('mock_test.html')

@app.route('/progress')
@login_required
@onboarding_required
def progress_dashboard():
    db = get_db()
    user = inject_user()
    quiz_result = None
    test_stats  = None
    if user:
        row = db.execute(
            'SELECT * FROM quiz_results WHERE user_id=? ORDER BY taken_at DESC LIMIT 1',
            (user['id'],)
        ).fetchone()
        if row: quiz_result = dict(row)
        ts = db.execute(
            'SELECT COUNT(*) as cnt, AVG(score) as avg_score FROM test_results WHERE user_id=?',
            (user['id'],)
        ).fetchone()
        if ts: test_stats = dict(ts)
    return render_template('progress.html',
        quiz_result=quiz_result, test_stats=test_stats)

# ─────────────────────────────────────────────
#  ERROR HANDLERS
# ─────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e): return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e): return render_template('500.html'), 500

# ─────────────────────────────────────────────
#  BOOT
# ─────────────────────────────────────────────
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)