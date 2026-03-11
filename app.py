import os
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'marg-darshak-secret-2025-major')
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "marg_darshak.db")

# ==================== DATABASE SETUP ====================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.join(BASE_DIR, "database"), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table - 3 types: student, graduate, professional
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        user_type TEXT DEFAULT 'student',  -- student / graduate / professional
        state TEXT,
        city TEXT,
        current_class TEXT,
        current_field TEXT,
        experience_years INTEGER DEFAULT 0,
        profile_complete INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Careers table
    c.execute('''CREATE TABLE IF NOT EXISTS careers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        description TEXT,
        roadmap TEXT,
        skills TEXT,
        youtube_links TEXT,
        required_skills TEXT,
        avg_salary_inr INTEGER,
        growth_rate TEXT,
        difficulty_level TEXT,
        education_required TEXT,
        top_colleges TEXT,
        job_roles TEXT
    )''')

    # Gyan Kosh table
    c.execute('''CREATE TABLE IF NOT EXISTS gyan_kosh (
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
    )''')

    # Learning Resources table
    c.execute('''CREATE TABLE IF NOT EXISTS learning_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT,
        title TEXT,
        url TEXT,
        difficulty TEXT,
        is_free INTEGER,
        quality_score REAL,
        platform TEXT,
        resource_type TEXT,
        duration_hours INTEGER,
        language TEXT
    )''')

    # Assessment Results table
    c.execute('''CREATE TABLE IF NOT EXISTS assessment_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        user_type TEXT,
        state TEXT,
        scores TEXT,  -- JSON: {analytical, creative, social, technical, entrepreneurial, leadership}
        recommended_careers TEXT,  -- JSON array
        personality_type TEXT,
        strengths TEXT,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # User bookmarks
    c.execute('''CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_type TEXT,  -- career / shloka / resource
        item_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    conn.commit()
    conn.close()

init_db()

# ==================== AUTH HELPERS ====================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        return dict(user) if user else None
    return None

# ==================== CONTEXT PROCESSOR ====================

@app.context_processor
def inject_user():
    return {'current_user': get_current_user()}

# ==================== HOME ====================

@app.route('/')
def index():
    try:
        conn = get_db_connection()
        career_count = conn.execute('SELECT COUNT(*) as count FROM careers').fetchone()['count']
        shloka_count = conn.execute('SELECT COUNT(*) as count FROM gyan_kosh').fetchone()['count']
        resource_count = conn.execute('SELECT COUNT(*) as count FROM learning_resources').fetchone()['count']
        user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
        conn.close()
        stats = {'careers': career_count, 'shlokas': shloka_count, 'resources': resource_count, 'users': user_count}
        return render_template('index.html', stats=stats)
    except Exception as e:
        return f"Error: {e}", 500

# ==================== AUTH ROUTES ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user_type = request.form.get('user_type', 'student')

        if not name or not email or not password:
            flash('All fields required', 'danger')
            return render_template('auth/register.html')

        try:
            conn = get_db_connection()
            existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
            if existing:
                flash('Email already registered', 'danger')
                conn.close()
                return render_template('auth/register.html')

            conn.execute(
                'INSERT INTO users (name, email, password_hash, user_type) VALUES (?, ?, ?, ?)',
                (name, email, hash_password(password), user_type)
            )
            conn.commit()
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            conn.close()

            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_type'] = user['user_type']

            flash(f'Welcome {name}! Complete your profile to get personalized guidance.', 'success')
            return redirect(url_for('complete_profile'))
        except Exception as e:
            flash(f'Registration error: {str(e)}', 'danger')

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password_hash = ?',
                           (email, hash_password(password))).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_type'] = user['user_type']
            flash(f'Welcome back, {user["name"]}!', 'success')

            if not user['profile_complete']:
                return redirect(url_for('complete_profile'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))


@app.route('/profile/complete', methods=['GET', 'POST'])
@login_required
def complete_profile():
    user = get_current_user()

    if request.method == 'POST':
        state = request.form.get('state', '')
        city = request.form.get('city', '')
        user_type = request.form.get('user_type', user['user_type'])

        # Type-specific fields
        current_class = request.form.get('current_class', '')
        current_field = request.form.get('current_field', '')
        experience_years = int(request.form.get('experience_years', 0) or 0)

        conn = get_db_connection()
        conn.execute('''UPDATE users SET state=?, city=?, user_type=?, current_class=?,
                       current_field=?, experience_years=?, profile_complete=1 WHERE id=?''',
                    (state, city, user_type, current_class, current_field, experience_years, user['id']))
        conn.commit()
        conn.close()

        session['user_type'] = user_type
        flash('Profile updated! Now take the assessment to get personalized recommendations.', 'success')
        return redirect(url_for('assessment_home'))

    return render_template('auth/complete_profile.html', user=user)


@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    conn = get_db_connection()

    # Get latest assessment
    latest_assessment = conn.execute(
        'SELECT * FROM assessment_results WHERE user_id = ? ORDER BY completed_at DESC LIMIT 1',
        (user['id'],)
    ).fetchone()

    # Bookmarks
    bookmarks = conn.execute(
        'SELECT * FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC LIMIT 5',
        (user['id'],)
    ).fetchall()

    conn.close()

    assessment_data = None
    if latest_assessment:
        assessment_data = dict(latest_assessment)
        assessment_data['scores'] = json.loads(assessment_data['scores'] or '{}')
        assessment_data['recommended_careers'] = json.loads(assessment_data['recommended_careers'] or '[]')

    return render_template('auth/dashboard.html',
                          user=user,
                          assessment=assessment_data,
                          bookmarks=[dict(b) for b in bookmarks])


# ==================== ASSESSMENT MODULE ====================

# Indian states list
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu & Kashmir", "Ladakh", "Chandigarh", "Puducherry"
]

# Questions for 3 user types
ASSESSMENT_QUESTIONS = {
    "student": [
        {
            "id": 1,
            "question": "School mein aapka sabse pasandida subject kaunsa hai?",
            "options": [
                {"text": "Maths aur Science", "scores": {"technical": 3, "analytical": 2}},
                {"text": "Art, Music ya Drama", "scores": {"creative": 3, "social": 1}},
                {"text": "Hindi, English ya Social Studies", "scores": {"social": 2, "creative": 2}},
                {"text": "Commerce ya Economics", "scores": {"entrepreneurial": 3, "analytical": 1}}
            ]
        },
        {
            "id": 2,
            "question": "Spare time mein aap kya karna pasand karte ho?",
            "options": [
                {"text": "Games khelta/khelta hoon ya puzzles solve karta/karti hoon", "scores": {"analytical": 3, "technical": 1}},
                {"text": "Drawing, writing ya music", "scores": {"creative": 3}},
                {"text": "Dosto ke saath bahar jaana ya log milna", "scores": {"social": 3, "leadership": 1}},
                {"text": "YouTube pe business/tech dekhna", "scores": {"entrepreneurial": 2, "technical": 1}}
            ]
        },
        {
            "id": 3,
            "question": "Agar school project mile to aap kya prefer karoge?",
            "options": [
                {"text": "Science experiment ya coding project", "scores": {"technical": 3, "analytical": 2}},
                {"text": "Poster banana ya skit karna", "scores": {"creative": 3, "social": 1}},
                {"text": "Group discussion ya presentation", "scores": {"social": 3, "leadership": 2}},
                {"text": "Business idea banana ya survey karna", "scores": {"entrepreneurial": 3, "analytical": 1}}
            ]
        },
        {
            "id": 4,
            "question": "Aap bade hokar khud ko kahan dekhte ho?",
            "options": [
                {"text": "Computer pe kaam karna ya invention karna", "scores": {"technical": 3}},
                {"text": "Apna business ya startup chalana", "scores": {"entrepreneurial": 3, "leadership": 2}},
                {"text": "Log ki madad karna — doctor, teacher, counselor", "scores": {"social": 3}},
                {"text": "Creative kaam — writer, artist, designer", "scores": {"creative": 3}}
            ]
        },
        {
            "id": 5,
            "question": "Class mein aap kaisa feel karte ho?",
            "options": [
                {"text": "Numbers aur formulas easy lagte hain", "scores": {"analytical": 3, "technical": 2}},
                {"text": "Stories aur debates zyada interesting lagti hain", "scores": {"social": 2, "creative": 2}},
                {"text": "Practical kaam karna pasand hai", "scores": {"technical": 2, "entrepreneurial": 1}},
                {"text": "Kuch naya banana ya experiment karna", "scores": {"creative": 2, "entrepreneurial": 2}}
            ]
        }
    ],
    "graduate": [
        {
            "id": 1,
            "question": "Aapka graduation field kaunsa tha / hai?",
            "options": [
                {"text": "Engineering / Technology / CS", "scores": {"technical": 3, "analytical": 2}},
                {"text": "Commerce / Business / MBA", "scores": {"entrepreneurial": 3, "analytical": 2}},
                {"text": "Arts / Humanities / Social Science", "scores": {"social": 3, "creative": 2}},
                {"text": "Science / Research / Medical", "scores": {"analytical": 3, "technical": 1}}
            ]
        },
        {
            "id": 2,
            "question": "College projects ya internships mein aapko kya zyada acha laga?",
            "options": [
                {"text": "Coding, data analysis ya technical solutions", "scores": {"technical": 3, "analytical": 2}},
                {"text": "Team lead karna ya presentations dena", "scores": {"leadership": 3, "social": 2}},
                {"text": "Design, content ya creative work", "scores": {"creative": 3}},
                {"text": "Business planning ya marketing strategy", "scores": {"entrepreneurial": 3, "analytical": 1}}
            ]
        },
        {
            "id": 3,
            "question": "Abhi aap career mein kya dhundh rahe ho?",
            "options": [
                {"text": "High paying MNC job — stability chahiye", "scores": {"analytical": 2, "technical": 2}},
                {"text": "Apna startup ya business shuru karna", "scores": {"entrepreneurial": 3, "leadership": 2}},
                {"text": "Government job ya research", "scores": {"analytical": 3, "social": 1}},
                {"text": "Creative field — media, arts, content", "scores": {"creative": 3, "social": 1}}
            ]
        },
        {
            "id": 4,
            "question": "Aapki sabse badi strength kya hai?",
            "options": [
                {"text": "Problem solving aur logical thinking", "scores": {"analytical": 3, "technical": 2}},
                {"text": "Log management aur communication", "scores": {"social": 3, "leadership": 2}},
                {"text": "Naya idea generate karna", "scores": {"creative": 3, "entrepreneurial": 2}},
                {"text": "Data se insights nikalna", "scores": {"analytical": 3, "technical": 1}}
            ]
        },
        {
            "id": 5,
            "question": "5 saal baad aap khud ko kahan dekhna chahte ho?",
            "options": [
                {"text": "Senior technical role — architect ya lead developer", "scores": {"technical": 3}},
                {"text": "Manager ya Director level", "scores": {"leadership": 3, "social": 2}},
                {"text": "Apna khud ka business", "scores": {"entrepreneurial": 3}},
                {"text": "Expert / Specialist apne field mein", "scores": {"analytical": 2, "creative": 2}}
            ]
        },
        {
            "id": 6,
            "question": "Currently aap kya kar rahe ho?",
            "options": [
                {"text": "Job dhundh raha/rahi hoon", "scores": {"analytical": 1}},
                {"text": "Koi freelance ya part-time kaam", "scores": {"entrepreneurial": 2}},
                {"text": "Higher studies ki taiyari", "scores": {"analytical": 2, "technical": 1}},
                {"text": "Family business mein hoon", "scores": {"entrepreneurial": 3, "leadership": 1}}
            ]
        }
    ],
    "professional": [
        {
            "id": 1,
            "question": "Aap currently kis field mein kaam karte/karti ho?",
            "options": [
                {"text": "IT / Software / Tech", "scores": {"technical": 3}},
                {"text": "Finance / Banking / Consulting", "scores": {"analytical": 3, "entrepreneurial": 1}},
                {"text": "Marketing / Sales / HR", "scores": {"social": 3, "leadership": 1}},
                {"text": "Healthcare / Education / NGO", "scores": {"social": 3, "analytical": 1}}
            ]
        },
        {
            "id": 2,
            "question": "Career mein ab aapka main goal kya hai?",
            "options": [
                {"text": "Promotion ya leadership role lena", "scores": {"leadership": 3, "social": 1}},
                {"text": "New skills seekhna aur domain switch karna", "scores": {"technical": 2, "analytical": 2}},
                {"text": "Apna business ya consultancy shuru karna", "scores": {"entrepreneurial": 3}},
                {"text": "Work-life balance improve karna", "scores": {"social": 2, "creative": 1}}
            ]
        },
        {
            "id": 3,
            "question": "Aapke kaam mein aapko kya sabse satisfying lagta hai?",
            "options": [
                {"text": "Complex problems solve karna", "scores": {"analytical": 3, "technical": 2}},
                {"text": "Team ko guide karna ya mentor karna", "scores": {"leadership": 3, "social": 2}},
                {"text": "Naya product ya idea build karna", "scores": {"creative": 3, "entrepreneurial": 2}},
                {"text": "Client relationships banana", "scores": {"social": 3, "entrepreneurial": 1}}
            ]
        },
        {
            "id": 4,
            "question": "Aap kaunsi emerging skill seekhna chahoge?",
            "options": [
                {"text": "AI / Machine Learning / Data Science", "scores": {"technical": 3, "analytical": 3}},
                {"text": "Business strategy ya MBA concepts", "scores": {"entrepreneurial": 3, "analytical": 1}},
                {"text": "Leadership aur management skills", "scores": {"leadership": 3, "social": 2}},
                {"text": "Digital marketing ya content creation", "scores": {"creative": 3, "social": 1}}
            ]
        },
        {
            "id": 5,
            "question": "Apne career mein aap sabse kisse inspire hote ho?",
            "options": [
                {"text": "Technical innovators — Elon Musk, Jeff Dean", "scores": {"technical": 3, "entrepreneurial": 1}},
                {"text": "Business leaders — Ratan Tata, Mukesh Ambani", "scores": {"entrepreneurial": 3, "leadership": 2}},
                {"text": "Social change makers — social entrepreneurs", "scores": {"social": 3, "leadership": 1}},
                {"text": "Creative professionals — filmmakers, writers", "scores": {"creative": 3}}
            ]
        },
        {
            "id": 6,
            "question": "Stress ke time aap kya karte ho?",
            "options": [
                {"text": "Problem ko systematically analyze karta/karti hoon", "scores": {"analytical": 3}},
                {"text": "Team ya friends se baat karta/karti hoon", "scores": {"social": 3, "leadership": 1}},
                {"text": "Creative outlet dhundhta/dhundti hoon", "scores": {"creative": 3}},
                {"text": "Agle steps plan karta/karti hoon", "scores": {"entrepreneurial": 2, "analytical": 1}}
            ]
        }
    ]
}


@app.route('/assessment')
def assessment_home():
    user = get_current_user()
    return render_template('assessment/home.html',
                          states=INDIAN_STATES,
                          user=user)


@app.route('/assessment/start', methods=['GET', 'POST'])
def assessment_start():
    if request.method == 'POST':
        user_type = request.form.get('user_type', 'student')
        state = request.form.get('state', '')

        session['assessment_user_type'] = user_type
        session['assessment_state'] = state

        questions = ASSESSMENT_QUESTIONS.get(user_type, ASSESSMENT_QUESTIONS['student'])
        return render_template('assessment/quiz.html',
                              questions=questions,
                              user_type=user_type,
                              state=state,
                              user=get_current_user())

    return redirect(url_for('assessment_home'))


@app.route('/assessment/submit', methods=['POST'])
def assessment_submit():
    try:
        data = request.get_json()
        user_type = data.get('user_type', 'student')
        state = data.get('state', '')
        answers = data.get('answers', {})

        # Calculate scores
        scores = {"technical": 0, "analytical": 0, "creative": 0,
                 "social": 0, "entrepreneurial": 0, "leadership": 0}

        questions = ASSESSMENT_QUESTIONS.get(user_type, ASSESSMENT_QUESTIONS['student'])

        for q in questions:
            answer_idx = answers.get(str(q['id']))
            if answer_idx is not None:
                option = q['options'][int(answer_idx)]
                for key, val in option['scores'].items():
                    scores[key] = scores.get(key, 0) + val

        # Determine top traits
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_trait = sorted_scores[0][0]
        second_trait = sorted_scores[1][0]

        # Personality type
        personality_map = {
            "technical": "The Builder 🔧",
            "analytical": "The Analyst 📊",
            "creative": "The Creator 🎨",
            "social": "The Helper 🤝",
            "entrepreneurial": "The Visionary 🚀",
            "leadership": "The Leader 👑"
        }
        personality_type = personality_map.get(top_trait, "The Explorer 🧭")

        # Strengths
        strengths_map = {
            "technical": ["Programming", "System Design", "Problem Solving", "Data Analysis"],
            "analytical": ["Critical Thinking", "Research", "Data Interpretation", "Strategy"],
            "creative": ["Innovation", "Design Thinking", "Content Creation", "Visual Arts"],
            "social": ["Communication", "Empathy", "Team Building", "People Management"],
            "entrepreneurial": ["Business Acumen", "Risk Taking", "Innovation", "Leadership"],
            "leadership": ["Decision Making", "Team Management", "Strategic Planning", "Mentoring"]
        }
        strengths = strengths_map.get(top_trait, []) + strengths_map.get(second_trait, [])[:2]

        # Get career recommendations from DB
        category_mapping = {
            "technical": ["Technology"],
            "analytical": ["Technology", "Business"],
            "creative": ["Creative"],
            "social": ["Business", "Creative"],
            "entrepreneurial": ["Business"],
            "leadership": ["Business"]
        }

        categories = category_mapping.get(top_trait, ["Technology"])
        if second_trait:
            categories += category_mapping.get(second_trait, [])

        conn = get_db_connection()

        # State-specific query — for now filter by difficulty based on state education level
        # (can be enhanced with real state data)
        career_query = '''SELECT * FROM careers WHERE category IN ({})
                         ORDER BY RANDOM() LIMIT 6'''.format(','.join('?' * len(set(categories))))

        careers = conn.execute(career_query, list(set(categories))).fetchall()

        # Also get skill-based resources
        skill_topics = {
            "technical": ["Programming", "Data Science", "Web Development"],
            "analytical": ["Data Science", "Machine Learning"],
            "creative": ["Design", "Digital Marketing"],
            "social": ["Communication", "Management"],
            "entrepreneurial": ["Business", "Digital Marketing"],
            "leadership": ["Management", "Business"]
        }

        topics = skill_topics.get(top_trait, ["Programming"])
        resources = conn.execute(
            'SELECT * FROM learning_resources WHERE topic IN ({}) AND is_free = 1 LIMIT 6'.format(
                ','.join('?' * len(topics))), topics
        ).fetchall()

        conn.close()

        # Save to DB if user logged in
        user = get_current_user()
        career_list = [dict(c) for c in careers]

        if user:
            conn = get_db_connection()
            conn.execute('''INSERT INTO assessment_results
                           (user_id, user_type, state, scores, recommended_careers, personality_type, strengths)
                           VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (user['id'], user_type, state,
                         json.dumps(scores),
                         json.dumps([c['title'] for c in career_list]),
                         personality_type,
                         json.dumps(strengths)))
            conn.commit()
            conn.close()

        return jsonify({
            'success': True,
            'scores': scores,
            'personality_type': personality_type,
            'strengths': strengths,
            'top_trait': top_trait,
            'careers': career_list,
            'resources': [dict(r) for r in resources],
            'state': state,
            'user_type': user_type
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/assessment/results')
def assessment_results():
    return render_template('assessment/results.html', user=get_current_user())


# ==================== CAREER MODULE ====================

@app.route('/career')
def career_home():
    return render_template('career/quiz.html', user=get_current_user())


@app.route('/career/quiz', methods=['GET', 'POST'])
def career_quiz():
    if request.method == 'POST':
        try:
            data = request.json
            interests = {
                'technical': data.get('technical', 0),
                'creative': data.get('creative', 0),
                'social': data.get('social', 0),
                'analytical': data.get('analytical', 0),
                'entrepreneurial': data.get('entrepreneurial', 0)
            }
            sorted_interests = sorted(interests.items(), key=lambda x: x[1], reverse=True)
            top_two = sorted_interests[:2]
            conn = get_db_connection()
            careers = []
            category_mapping = {
                'technical': 'Technology', 'creative': 'Creative',
                'social': 'Business', 'analytical': 'Technology', 'entrepreneurial': 'Business'
            }
            for interest, score in top_two:
                category = category_mapping.get(interest, 'Technology')
                results = conn.execute('SELECT * FROM careers WHERE category = ? LIMIT 3', (category,)).fetchall()
                for row in results:
                    careers.append(dict(row))
            conn.close()
            unique_careers = []
            seen_ids = set()
            for career in careers:
                if career['id'] not in seen_ids:
                    unique_careers.append(career)
                    seen_ids.add(career['id'])
            return jsonify({'success': True, 'interests': interests, 'careers': unique_careers[:5]})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return render_template('career/quiz.html', user=get_current_user())


@app.route('/career/browse')
def career_browse():
    try:
        conn = get_db_connection()
        category = request.args.get('category', 'all')
        search = request.args.get('search', '').strip()

        query = 'SELECT * FROM careers WHERE 1=1'
        params = []

        if category != 'all':
            query += ' AND category = ?'
            params.append(category)

        if search:
            query += ' AND (title LIKE ? OR description LIKE ? OR required_skills LIKE ?)'
            params += [f'%{search}%', f'%{search}%', f'%{search}%']

        query += ' ORDER BY title'
        careers = conn.execute(query, params).fetchall()
        categories = conn.execute('SELECT DISTINCT category FROM careers').fetchall()
        conn.close()

        return render_template('career/browse.html',
                             careers=[dict(c) for c in careers],
                             categories=[r['category'] for r in categories],
                             selected_category=category,
                             search=search,
                             user=get_current_user())
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/career/detail/<int:career_id>')
def career_detail(career_id):
    try:
        conn = get_db_connection()
        career = conn.execute('SELECT * FROM careers WHERE id = ?', (career_id,)).fetchone()

        if not career:
            return "Career not found", 404

        career_dict = dict(career)

        # Get related resources for this career's skills
        skills = career_dict.get('required_skills', '').split(';')[:3] if career_dict.get('required_skills') else []
        resources = []
        if skills:
            placeholders = ','.join('?' * len(skills))
            resources = conn.execute(
                f'SELECT * FROM learning_resources WHERE topic IN ({placeholders}) LIMIT 6',
                skills
            ).fetchall()

        # Related careers
        related = conn.execute(
            'SELECT * FROM careers WHERE category = ? AND id != ? LIMIT 4',
            (career_dict.get('category', ''), career_id)
        ).fetchall()

        conn.close()

        return render_template('career/detail.html',
                             career=career_dict,
                             resources=[dict(r) for r in resources],
                             related_careers=[dict(r) for r in related],
                             user=get_current_user())
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error: {e}", 500


# ==================== GYAN KOSH ====================

@app.route('/gyan')
def gyan_home():
    try:
        conn = get_db_connection()
        shloka = conn.execute('SELECT * FROM gyan_kosh ORDER BY RANDOM() LIMIT 1').fetchone()
        conn.close()
        if shloka:
            return render_template('gyan/daily.html', shloka=dict(shloka), user=get_current_user())
        return "No shlokas found", 500
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/gyan/search')
def gyan_search():
    try:
        query = request.args.get('q', '').strip()
        conn = get_db_connection()
        if query:
            pattern = f'%{query}%'
            shlokas = conn.execute('''SELECT * FROM gyan_kosh
                WHERE hindi_meaning LIKE ? OR english_meaning LIKE ?
                OR practical_application LIKE ? OR tags LIKE ?
            ''', (pattern, pattern, pattern, pattern)).fetchall()
        else:
            shlokas = conn.execute('SELECT * FROM gyan_kosh ORDER BY chapter, verse_number LIMIT 20').fetchall()
        conn.close()
        return render_template('gyan/search.html',
                             shlokas=[dict(s) for s in shlokas],
                             query=query,
                             user=get_current_user())
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/gyan/detail/<int:shloka_id>')
def gyan_detail(shloka_id):
    try:
        conn = get_db_connection()
        shloka = conn.execute('SELECT * FROM gyan_kosh WHERE id = ?', (shloka_id,)).fetchone()
        conn.close()
        if shloka:
            return render_template('gyan/detail.html', shloka=dict(shloka), user=get_current_user())
        return "Shloka not found", 404
    except Exception as e:
        return f"Error: {e}", 500


# ==================== SKILL SAATHI ====================

@app.route('/skill')
def skill_home():
    try:
        conn = get_db_connection()
        topics = conn.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
        resources = conn.execute('SELECT * FROM learning_resources ORDER BY quality_score DESC LIMIT 12').fetchall()
        conn.close()
        return render_template('skill/browse.html',
                             topics=[r['topic'] for r in topics],
                             resources=[dict(r) for r in resources],
                             selected_topic='all',
                             selected_difficulty='all',
                             free_only=False,
                             user=get_current_user())
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/skill/browse')
def skill_browse():
    try:
        topic = request.args.get('topic', 'all')
        difficulty = request.args.get('difficulty', 'all')
        free_only = request.args.get('free', 'false') == 'true'
        search = request.args.get('search', '').strip()

        conn = get_db_connection()
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
        if search:
            query += ' AND (title LIKE ? OR topic LIKE ?)'
            params += [f'%{search}%', f'%{search}%']

        query += ' ORDER BY quality_score DESC'
        resources = conn.execute(query, params).fetchall()
        topics = conn.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
        conn.close()

        return render_template('skill/browse.html',
                             resources=[dict(r) for r in resources],
                             topics=[r['topic'] for r in topics],
                             selected_topic=topic,
                             selected_difficulty=difficulty,
                             free_only=free_only,
                             user=get_current_user())
    except Exception as e:
        return f"Error: {e}", 500


# ==================== BOOKMARK API ====================

@app.route('/api/bookmark', methods=['POST'])
@login_required
def toggle_bookmark():
    data = request.get_json()
    item_type = data.get('type')
    item_id = data.get('id')
    user = get_current_user()

    conn = get_db_connection()
    existing = conn.execute(
        'SELECT id FROM bookmarks WHERE user_id=? AND item_type=? AND item_id=?',
        (user['id'], item_type, item_id)
    ).fetchone()

    if existing:
        conn.execute('DELETE FROM bookmarks WHERE id=?', (existing['id'],))
        conn.commit()
        conn.close()
        return jsonify({'bookmarked': False})
    else:
        conn.execute('INSERT INTO bookmarks (user_id, item_type, item_id) VALUES (?,?,?)',
                    (user['id'], item_type, item_id))
        conn.commit()
        conn.close()
        return jsonify({'bookmarked': True})


# ==================== AI CHATBOT (Claude API) ====================

@app.route('/chat')
def chat_page():
    return render_template('chat.html', user=get_current_user())


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Career counseling chatbot powered by Groq API (llama3-70b)"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        history = data.get('history', [])
        user = get_current_user()

        # Build personalized context
        user_context = ""
        if user:
            user_context = f"""
Current User Profile:
- Name: {user['name']}
- Type: {user['user_type']} (student / graduate / professional)
- State: {user.get('state', 'Not specified')}
- Field: {user.get('current_field', 'Not specified')}
- Experience: {user.get('experience_years', 0)} years
"""

        system_prompt = f"""Tum Marg Darshak AI ho — India ke students aur professionals ke liye ek friendly aur knowledgeable career counselor.

Tum Hinglish mein baat karo (Hindi + English mix) jab user Hinglish use kare. Pure Hindi ya pure English bhi theek hai based on user preference.

Tumhari expertise:
- Indian education system: IIT NIT IIIT State Universities deemed universities
- Entrance exams: JEE NEET CAT GATE UPSC SSC CLAT NDA
- Career paths: Technology Business Creative Healthcare Government Legal Education
- Skills to learn: Python Data Science Web Dev Digital Marketing MBA prep UPSC prep
- Salary ranges in INR: Entry level to senior level for all major careers
- State-specific opportunities: Government jobs local companies and colleges in each state
- Certifications: Google AWS Coursera Udemy free vs paid
- Data Science and AI/ML career roadmap specifically (very high demand topic)
- Startup ecosystem: How to start a startup in India funding and incubators
- Study abroad: GRE IELTS TOEFL guidance for Indian students

{user_context}

Response Style:
- Warm encouraging aur practical raho
- Specific actionable advice do with exact steps
- Salary INR mein batao (e.g. 8-15 LPA entry level)
- Specific college names aur certification names mention karo
- Short and crisp responses — 3-5 paragraphs maximum
- Emojis thoda use karo for friendliness
- Medical ya legal advice mat do — career and education only

Agar user confused ho toh 3 concrete next steps do.
Agar skills pooche toh free resources bhi suggest karo (YouTube Coursera etc)."""

        GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

        if not GROQ_API_KEY:
            # Fallback: rule-based responses if no API key
            return jsonify({
                'success': True,
                'message': get_fallback_response(user_message)
            })

        import urllib.request

        messages = [{"role": "system", "content": system_prompt}]
        messages += history[-8:]
        messages.append({"role": "user", "content": user_message})

        payload = json.dumps({
            "model": "llama3-70b-8192",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800,
            "stream": False
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {GROQ_API_KEY}'
            }
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode('utf-8'))
            assistant_message = result['choices'][0]['message']['content']

        return jsonify({'success': True, 'message': assistant_message})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': True,
            'message': get_fallback_response(data.get('message', ''))
        })


def get_fallback_response(message):
    """Smart rule-based fallback when no API key is set"""
    msg = message.lower()

    if any(w in msg for w in ['data science', 'ml', 'machine learning', 'ai career']):
        return """**Data Science Career Roadmap 🎯**

Data Science India mein ek of the best paying careers hai! Yahan ek clear path hai:

**Phase 1 — Foundation (3-6 months):**
- Python seekho (YouTube pe free courses hain — Apna College, Code with Harry)
- Statistics basics: mean median standard deviation probability
- SQL seekho — every data job requires it

**Phase 2 — Core Skills (6-12 months):**
- Pandas, NumPy, Matplotlib (data manipulation and visualization)
- Scikit-learn se Machine Learning algorithms
- Kaggle competitions start karo

**Phase 3 — Advanced (12-18 months):**
- Deep Learning: TensorFlow ya PyTorch
- NLP ya Computer Vision choose karo

**Salary:** Entry level ₹6-10 LPA, 3 years experience ₹15-30 LPA

Best free resources: Coursera (Andrew Ng ML course), Kaggle Learn, YouTube (Krish Naik channel)

Koi specific topic mein aur detail chahiye? 😊"""

    elif any(w in msg for w in ['software', 'coding', 'developer', 'programming']):
        return """**Software Developer Career Path 💻**

Software development India mein sabse zyada jobs wala field hai!

**Roadmap:**
1. Programming language chuno: Python (easiest) ya Java ya C++ (for competitive)
2. DSA (Data Structures and Algorithms) — interview crackers ke liye must
3. Web Development ya App Development ya Backend — koi ek choose karo
4. 2-3 projects GitHub pe daalo
5. Internship dhundo — even unpaid pehle

**Top Skills:** Python/Java, DSA, React/Node.js, Git, System Design

**Salary:** Fresher ₹4-12 LPA (IIT/BITS), ₹3-6 LPA (other colleges), 5 years ₹15-35 LPA

**Free Resources:** Apna College YouTube, LeetCode for DSA, freeCodeCamp for web

Kya specific tech stack mein guidance chahiye? 🚀"""

    elif any(w in msg for w in ['upsc', 'ias', 'ips', 'civil service', 'government']):
        return """**UPSC Civil Services Guide 🏛️**

UPSC India ka sabse prestigious exam hai. Challenging but achievable with right strategy!

**Selection Process:**
1. Prelims (June) — GS Paper 1 + CSAT
2. Mains (September) — 9 papers
3. Interview/Personality Test

**Preparation Timeline:** Minimum 1-2 years dedicated preparation

**Strategy:**
- NCERT books 6th to 12th pehle complete karo
- Current Affairs: The Hindu ya Indian Express daily
- Answer writing practice bahut important hai
- Previous year papers solve karo

**Top Coaching:** Drishti IAS, Vision IAS, Shankar IAS (Delhi)
**Online Free:** Drishti IAS YouTube, UPSC Wallah

**Age:** 21-32 years (General), 21-35 (OBC), 21-37 (SC/ST)

Kaunsa subject ya topic mein guidance chahiye? 📚"""

    elif any(w in msg for w in ['mba', 'cat', 'management', 'business school']):
        return """**MBA/CAT Preparation Guide 📊**

MBA India mein career accelerator hai especially IIM se!

**CAT Exam:**
- Sections: VARC, DILR, Quantitative Aptitude
- Score 99+ percentile for IIM A B C
- 85+ for good IIMs

**Preparation (1 year):**
- Quants: Arun Sharma book + YouTube
- VARC: Reading newspapers daily + RC practice
- DILR: Practice sets daily

**Top Colleges:** IIM A B C L I K, MDI, XLRI, ISB, FMS Delhi

**Salary After MBA:** IIM A placement average ₹25-35 LPA, other IIMs ₹12-20 LPA

**Free Resources:** Unacademy CAT, IIM CAT YouTube channels, 2IIM for Quants

Kya work experience hai ya fresher ho? Strategy alag hogi! 💡"""

    elif any(w in msg for w in ['salary', 'income', 'earning', 'pay']):
        return """**Indian Career Salary Guide 💰**

2024 mein India ke top paying careers:

**Technology:**
- Software Engineer: ₹4-40 LPA (experience based)
- Data Scientist: ₹6-50 LPA
- Cloud Architect: ₹15-80 LPA
- Cybersecurity: ₹6-40 LPA

**Business/Finance:**
- CA: ₹6-40 LPA
- Investment Banker: ₹8-1 Crore+
- Product Manager: ₹12-60 LPA

**Healthcare:**
- Doctor (Specialist): ₹12-1 Crore+
- Pharmacist: ₹3-8 LPA

**Government:**
- IAS: ₹56,100-2,50,000/month + perks

**Key Factor:** Skills matter more than degree. A self-taught developer with strong portfolio can earn ₹15 LPA without a degree.

Kaunse career ki salary detail chahiye? 🎯"""

    else:
        return """Namaste! 🙏 Main Marg Darshak AI hoon — aapka personal career counselor!

Main aapki help kar sakta hoon:
- **Career Selection** — student/graduate/professional ke liye
- **Skill Roadmap** — kya seekhna chahiye step by step
- **Salary Info** — Indian market mein actual packages
- **Exam Prep** — JEE NEET CAT UPSC GATE guidance
- **Job Search** — resume tips interview prep freelancing

Apna specific sawal pooch — jitna specific utna better guidance dunga! 😊

Jaise: *"Main 12th PCM student hoon UP se, Data Science mein career banana chahta hoon, kahan se shuru karoon?"*"""


# ==================== STATS API ====================

@app.route('/api/stats')
def api_stats():
    try:
        conn = get_db_connection()
        stats = {
            'careers': conn.execute('SELECT COUNT(*) as c FROM careers').fetchone()['c'],
            'shlokas': conn.execute('SELECT COUNT(*) as c FROM gyan_kosh').fetchone()['c'],
            'resources': conn.execute('SELECT COUNT(*) as c FROM learning_resources').fetchone()['c'],
            'users': conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c'],
            'assessments': conn.execute('SELECT COUNT(*) as c FROM assessment_results').fetchone()['c']
        }
        conn.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


# ==================== DB LOADER ====================

@app.route('/admin/load-data')
def load_data():
    """Load CSV data into database"""
    try:
        import csv
        conn = get_db_connection()

        # Load careers
        careers_path = os.path.join(BASE_DIR, 'data', 'careers.csv')
        if os.path.exists(careers_path):
            conn.execute('DELETE FROM careers')
            with open(careers_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    conn.execute('''INSERT INTO careers
                        (title, category, description, required_skills, avg_salary_inr,
                         growth_rate, difficulty_level, education_required, top_colleges, job_roles)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (row.get('title'), row.get('category'), row.get('description'),
                         row.get('required_skills'), row.get('avg_salary_inr'),
                         row.get('growth_rate'), row.get('difficulty_level'),
                         row.get('education_required'), row.get('top_colleges'), row.get('job_roles')))

        # Load shlokas
        shlokas_path = os.path.join(BASE_DIR, 'data', 'shlokas.csv')
        if os.path.exists(shlokas_path):
            conn.execute('DELETE FROM gyan_kosh')
            with open(shlokas_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    conn.execute('''INSERT INTO gyan_kosh
                        (source, chapter, verse_number, sanskrit_text, hindi_meaning,
                         english_meaning, practical_application, tags, audio_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (row.get('source'), row.get('chapter'), row.get('verse_number'),
                         row.get('sanskrit_text'), row.get('hindi_meaning'),
                         row.get('english_meaning'), row.get('practical_application'),
                         row.get('tags'), row.get('audio_url')))

        # Load resources
        resources_path = os.path.join(BASE_DIR, 'data', 'resources.csv')
        if os.path.exists(resources_path):
            conn.execute('DELETE FROM learning_resources')
            with open(resources_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    is_free = 1 if str(row.get('is_free', 'FALSE')).upper() in ['TRUE', '1', 'YES'] else 0
                    conn.execute('''INSERT INTO learning_resources
                        (title, topic, platform, resource_type, url, difficulty,
                         duration_hours, quality_score, language, is_free)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (row.get('title'), row.get('topic'), row.get('platform'),
                         row.get('resource_type'), row.get('url'), row.get('difficulty'),
                         row.get('duration_hours'), row.get('quality_score'),
                         row.get('language'), is_free))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Data loaded successfully!'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
