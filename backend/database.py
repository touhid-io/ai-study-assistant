import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
import os

# Define the absolute path for the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, 'study_assistant.db')

class Database:
    
    def __init__(self, db_path=DEFAULT_DB_PATH): # Use the absolute path as default
        self.db_path = db_path
        print(f"Database connection path set to: {self.db_path}") # Debugging line
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    word_count INTEGER,
                    language TEXT DEFAULT 'en', 
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    question_hash TEXT NOT NULL,
                    options TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    explanation TEXT,
                    cognitive_level TEXT,
                    times_shown INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id),
                    UNIQUE(document_id, question_hash)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    total_questions INTEGER,
                    correct_answers INTEGER,
                    status TEXT DEFAULT 'started',
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    session_id INTEGER NOT NULL,
                    user_answer TEXT,
                    is_correct BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES questions(id),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            ''')
            
            conn.execute("PRAGMA foreign_keys = ON")
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_document_hash 
                ON documents(content_hash)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_question_document 
                ON questions(document_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_attempts_question 
                ON user_attempts(question_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_attempts_session
                ON user_attempts(session_id)
            ''')
            
            print("Database initialized successfully")
    
    def save_document(self, filename, content, content_hash, word_count, language='en'):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO documents (filename, content, content_hash, word_count, language)
                VALUES (?, ?, ?, ?, ?)
            ''', (filename, content, content_hash, word_count, language))
            
            doc_id = cursor.lastrowid
            print(f"Document saved with ID: {doc_id}")
            return doc_id
    
    def get_document(self, document_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM documents WHERE id = ?',
                (document_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_question(self, document_id, question_data, question_hash):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO questions 
                    (document_id, question_text, question_hash, options, 
                     correct_answer, explanation, cognitive_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    document_id,
                    question_data['question'],
                    question_hash,
                    json.dumps(question_data['options'], ensure_ascii=False),
                    question_data['correct_answer'],
                    question_data.get('explanation', ''),
                    question_data.get('cognitive_level', 'Unknown')
                ))
                
                q_id = cursor.lastrowid
                print(f"Question saved with ID: {q_id}")
                return q_id
                
            except sqlite3.IntegrityError:
                print(f"Question with hash {question_hash} already exists for document {document_id}")
                return None
    
    def question_exists(self, document_id, question_hash):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM questions 
                WHERE document_id = ? AND question_hash = ?
            ''', (document_id, question_hash))
            return cursor.fetchone() is not None
    
    def get_questions_by_document(self, document_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, question_text, options, correct_answer, 
                       explanation, cognitive_level
                FROM questions
                WHERE document_id = ?
                ORDER BY id
            ''', (document_id,))
            
            questions = []
            for row in cursor.fetchall():
                q = dict(row)
                q['options'] = json.loads(q['options'])
                questions.append(q)
            
            return questions

    def start_session(self, document_id, total_questions):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (document_id, total_questions)
                VALUES (?, ?)
            ''', (document_id, total_questions))
            return cursor.lastrowid
            
    def end_session(self, session_id, correct_answers):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions
                SET end_time = CURRENT_TIMESTAMP,
                    correct_answers = ?,
                    status = 'completed'
                WHERE id = ?
            ''', (correct_answers, session_id))

    def save_attempt(self, session_id, question_id, user_answer, is_correct):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_attempts (session_id, question_id, user_answer, is_correct)
                VALUES (?, ?, ?, ?)
            ''', (session_id, question_id, user_answer, 1 if is_correct else 0))
            
            cursor.execute('''
                UPDATE questions 
                SET times_shown = times_shown + 1
                WHERE id = ?
            ''', (question_id,))
    
    def get_document_statistics(self, document_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as total FROM questions
                WHERE document_id = ?
            ''', (document_id,))
            total_questions = cursor.fetchone()['total']
            
            cursor.execute('''
                SELECT COUNT(*) as total FROM user_attempts ua
                JOIN questions q ON ua.question_id = q.id
                WHERE q.document_id = ?
            ''', (document_id,))
            total_attempts = cursor.fetchone()['total']
            
            cursor.execute('''
                SELECT COUNT(*) as correct FROM user_attempts ua
                JOIN questions q ON ua.question_id = q.id
                WHERE q.document_id = ? AND ua.is_correct = 1
            ''', (document_id,))
            correct_attempts = cursor.fetchone()['correct']
            
            accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
            
            return {
                'total_questions': total_questions,
                'total_attempts': total_attempts,
                'correct_attempts': correct_attempts,
                'accuracy': round(accuracy, 2)
            }

    def get_session_history(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    s.id, 
                    s.start_time, 
                    s.total_questions, 
                    s.correct_answers,
                    d.filename
                FROM sessions s
                JOIN documents d ON s.document_id = d.id
                WHERE s.status = 'completed'
                ORDER BY s.start_time DESC
                LIMIT 10
            ''')
            sessions = []
            for row in cursor.fetchall():
                s = dict(row)
                percentage = 0
                if s['total_questions'] and s['total_questions'] > 0:
                    percentage = round((s['correct_answers'] / s['total_questions']) * 100)
                
                sessions.append({
                    'id': s['id'],
                    'fileName': s['filename'],
                    'date': s['start_time'],
                    'score': s['correct_answers'],
                    'total': s['total_questions'],
                    'percentage': percentage
                })
            return sessions

    def get_overall_analytics(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE status = 'completed'")
            total_sessions = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(total_questions) FROM sessions WHERE status = 'completed'")
            total_questions = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(correct_answers) FROM sessions WHERE status = 'completed'")
            total_correct = cursor.fetchone()[0] or 0
            
            avg_score = 0
            if total_sessions > 0 and total_questions > 0:
                cursor.execute('''
                    SELECT AVG(CAST(correct_answers AS REAL) / total_questions) * 100
                    FROM sessions
                    WHERE status = 'completed' AND total_questions > 0
                ''')
                avg_score_result = cursor.fetchone()[0]
                avg_score = round(avg_score_result, 2) if avg_score_result is not None else 0

            return {
                'total_sessions': total_sessions,
                'total_questions': total_questions,
                'avg_score': avg_score
            }

    def get_session_details(self, session_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            session = cursor.fetchone()
            if not session:
                return None
            
            cursor.execute('''
                SELECT q.question_text, q.options, q.correct_answer, q.explanation, ua.user_answer
                FROM user_attempts ua
                JOIN questions q ON ua.question_id = q.id
                WHERE ua.session_id = ? AND ua.is_correct = 0
            ''', (session_id,))
            
            wrong_answers = []
            for row in cursor.fetchall():
                wrong_answers.append({
                    'question': row['question_text'],
                    'options': json.loads(row['options']),
                    'user_answer': row['user_answer'],
                    'correct_answer': row['correct_answer'],
                    'explanation': row['explanation']
                })
            
            return {
                'total': session['total_questions'],
                'correct': session['correct_answers'],
                'wrong': wrong_answers
            }
            
    def delete_session(self, session_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("DELETE FROM user_attempts WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            
            print(f"Session {session_id} deleted successfully")
            return cursor.rowcount > 0

    def clear_all_data(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute('DELETE FROM user_attempts')
            cursor.execute('DELETE FROM questions')
            cursor.execute('DELETE FROM sessions')
            cursor.execute('DELETE FROM documents')
            print("All data cleared from database")