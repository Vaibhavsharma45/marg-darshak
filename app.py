from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = '4e2dead963bab8f59c771f2d98efc815'

# ADD THIS - Make request available in templates
@app.context_processor
def inject_request():
    return dict(request=request)

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('database/marg_darshak.db')
    conn.row_factory = sqlite3.Row
    return conn

# ... rest of your routes

# ==================== HOME PAGE ====================
@app.route('/')
def index():
    """Homepage with 3 main modules"""
    try:
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
    except Exception as e:
        print(f"Homepage error: {e}")
        return f"Error: {e}", 500

# ==================== CAREER MODULE ====================
@app.route('/career')
def career_home():
    """Career guidance homepage"""
    return render_template('career/quiz.html')

@app.route('/career/quiz', methods=['GET', 'POST'])
def career_quiz():
    """Career interest quiz"""
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
                'technical': 'Technology',
                'creative': 'Creative',
                'social': 'Business',
                'analytical': 'Technology',
                'entrepreneurial': 'Business'
            }
            
            for interest, score in top_two:
                category = category_mapping.get(interest, 'Technology')
                results = conn.execute(
                    'SELECT * FROM careers WHERE category = ? LIMIT 3',
                    (category,)
                ).fetchall()
                for row in results:
                    careers.append(dict(row))
            
            conn.close()
            
            unique_careers = []
            seen_ids = set()
            for career in careers:
                if career['id'] not in seen_ids:
                    unique_careers.append(career)
                    seen_ids.add(career['id'])
            
            return jsonify({
                'success': True,
                'interests': interests,
                'careers': unique_careers[:5]
            })
        except Exception as e:
            print(f"Quiz error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return render_template('career/quiz.html')

@app.route('/career/results')
def career_results():
    """Display career quiz results"""
    return render_template('career/results.html')

@app.route('/career/browse')
def career_browse():
    """Browse all careers"""
    try:
        conn = get_db_connection()
        
        category = request.args.get('category', 'all')
        
        if category == 'all':
            careers = conn.execute('SELECT * FROM careers ORDER BY title').fetchall()
        else:
            careers = conn.execute('SELECT * FROM careers WHERE category = ? ORDER BY title', (category,)).fetchall()
        
        categories = conn.execute('SELECT DISTINCT category FROM careers').fetchall()
        
        conn.close()
        
        career_list = []
        for row in careers:
            career_list.append(dict(row))
        
        category_list = []
        for row in categories:
            category_list.append(row['category'])
        
        return render_template('career/browse.html', 
                             careers=career_list,
                             categories=category_list,
                             selected_category=category)
    except Exception as e:
        print(f"Browse error: {e}")
        return f"Error: {e}", 500

@app.route('/career/detail/<int:career_id>')
def career_detail(career_id):
    """Detailed career view with roadmap"""
    try:
        conn = get_db_connection()
        career = conn.execute('SELECT * FROM careers WHERE id = ?', (career_id,)).fetchone()
        conn.close()
        
        if career:
            career_dict = dict(career)
            print(f"Career found: {career_dict['title']}")  # Debug
            return render_template('career/detail.html', career=career_dict)
        else:
            print(f"Career not found: {career_id}")  # Debug
            return "Career not found", 404
    except Exception as e:
        print(f"Detail error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h2>Error: {e}</h2><a href='/career/browse'>Back to Browse</a>", 500

# ==================== GYAN KOSH MODULE ====================
@app.route('/gyan')
def gyan_home():
    """Gyan Kosh homepage - Daily Shloka"""
    try:
        conn = get_db_connection()
        
        count = conn.execute('SELECT COUNT(*) as count FROM gyan_kosh').fetchone()['count']
        
        if count == 0:
            conn.close()
            return """
            <div style="text-align: center; padding: 50px;">
                <h2>No data available</h2>
                <p>Please run: <code>python database/load_csv_to_db.py</code></p>
                <a href="/" style="padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px;">Back to Home</a>
            </div>
            """, 500
        
        shloka = conn.execute('SELECT * FROM gyan_kosh ORDER BY RANDOM() LIMIT 1').fetchone()
        conn.close()
        
        if shloka:
            return render_template('gyan/daily.html', shloka=dict(shloka))
        else:
            return "No shlokas found", 500
            
    except Exception as e:
        print(f"Gyan home error: {e}")
        return f"<h2>Error: {e}</h2><a href='/'>Back to Home</a>", 500

@app.route('/gyan/search')
def gyan_search():
    """Search shlokas"""
    try:
        query = request.args.get('q', '').strip()
        
        conn = get_db_connection()
        
        if query:
            search_pattern = f'%{query}%'
            shlokas = conn.execute('''
                SELECT * FROM gyan_kosh 
                WHERE hindi_meaning LIKE ? 
                OR english_meaning LIKE ? 
                OR practical_application LIKE ?
                OR tags LIKE ?
            ''', (search_pattern, search_pattern, search_pattern, search_pattern)).fetchall()
        else:
            shlokas = conn.execute('SELECT * FROM gyan_kosh ORDER BY chapter, verse_number LIMIT 20').fetchall()
        
        conn.close()
        
        shloka_list = []
        for row in shlokas:
            shloka_list.append(dict(row))
        
        return render_template('gyan/search.html', 
                             shlokas=shloka_list,
                             query=query)
    except Exception as e:
        print(f"Search error: {e}")
        return f"Error: {e}", 500

@app.route('/gyan/detail/<int:shloka_id>')
def gyan_detail(shloka_id):
    """Detailed shloka view"""
    try:
        conn = get_db_connection()
        shloka = conn.execute('SELECT * FROM gyan_kosh WHERE id = ?', (shloka_id,)).fetchone()
        conn.close()
        
        if shloka:
            return render_template('gyan/detail.html', shloka=dict(shloka))
        return "Shloka not found", 404
    except Exception as e:
        print(f"Gyan detail error: {e}")
        return f"Error: {e}", 500

# ==================== SKILL SAATHI MODULE ====================
@app.route('/skill')
def skill_home():
    """Skill Saathi homepage"""
    try:
        conn = get_db_connection()
        
        count = conn.execute('SELECT COUNT(*) as count FROM learning_resources').fetchone()['count']
        
        if count == 0:
            conn.close()
            return """
            <div style="text-align: center; padding: 50px;">
                <h2>No resources available</h2>
                <p>Please run: <code>python database/load_csv_to_db.py</code></p>
                <a href="/" style="padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px;">Back to Home</a>
            </div>
            """, 500
        
        topics = conn.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
        resources = conn.execute('SELECT * FROM learning_resources ORDER BY quality_score DESC LIMIT 12').fetchall()
        
        conn.close()
        
        topic_list = []
        for row in topics:
            topic_list.append(row['topic'])
        
        resource_list = []
        for row in resources:
            resource_list.append(dict(row))
        
        return render_template('skill/browse.html', 
                             topics=topic_list,
                             resources=resource_list,
                             selected_topic='all',
                             selected_difficulty='all',
                             free_only=False)
                             
    except Exception as e:
        print(f"Skill home error: {e}")
        return f"<h2>Error: {e}</h2><a href='/'>Back to Home</a>", 500

@app.route('/skill/browse')
def skill_browse():
    """Browse learning resources with filters"""
    try:
        topic = request.args.get('topic', 'all')
        difficulty = request.args.get('difficulty', 'all')
        free_only = request.args.get('free', 'false') == 'true'
        
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
        
        query += ' ORDER BY quality_score DESC'
        
        resources = conn.execute(query, params).fetchall()
        topics = conn.execute('SELECT DISTINCT topic FROM learning_resources').fetchall()
        
        conn.close()
        
        resource_list = []
        for row in resources:
            resource_list.append(dict(row))
        
        topic_list = []
        for row in topics:
            topic_list.append(row['topic'])
        
        return render_template('skill/browse.html',
                             resources=resource_list,
                             topics=topic_list,
                             selected_topic=topic,
                             selected_difficulty=difficulty,
                             free_only=free_only)
    except Exception as e:
        print(f"Skill browse error: {e}")
        return f"Error: {e}", 500

# ==================== API ROUTES ====================
@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    try:
        conn = get_db_connection()
        
        stats = {
            'careers': conn.execute('SELECT COUNT(*) as count FROM careers').fetchone()['count'],
            'shlokas': conn.execute('SELECT COUNT(*) as count FROM gyan_kosh').fetchone()['count'],
            'resources': conn.execute('SELECT COUNT(*) as count FROM learning_resources').fetchone()['count']
        }
        
        categories = conn.execute('SELECT DISTINCT category FROM careers').fetchall()
        stats['categories'] = len(categories)
        
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

# ==================== RUN APP ====================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)