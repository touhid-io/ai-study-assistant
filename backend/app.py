from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import google.generativeai as genai
import json
import hashlib
import time
from document_processor import DocumentProcessor
from database import Database
import os
from dotenv import load_dotenv
import numpy as np
from numpy.linalg import norm

load_dotenv()

app = Flask(__name__)
CORS(app)

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

generation_model = genai.GenerativeModel('gemini-2.0-flash-exp') 

db = Database()
doc_processor = DocumentProcessor()

document_embeddings_cache = {}

def get_document_chunks(document_text):
    chunks = document_text.split('\n\n')
    return [chunk for chunk in chunks if chunk.strip() and len(chunk.split()) > 10]

def get_or_create_document_embeddings(document_id, document_text):
    if document_id in document_embeddings_cache:
        return document_embeddings_cache[document_id]
    
    print(f"Creating new embeddings for document {document_id}...")
    chunks = get_document_chunks(document_text)
    
    if not chunks:
        chunks = [document_text]
        
    try:
        response = genai.embed_content(
            model='models/text-embedding-004',
            task_type="retrieval_document",
            content=chunks
        )
        embeddings = response['embedding']
        document_embeddings_cache[document_id] = (chunks, embeddings)
        print(f"Embeddings cached for document {document_id}")
        return chunks, embeddings
    except Exception as e:
        print(f"Error creating embeddings: {e}")
        try:
            response = genai.embed_content(
                model='models/embedding-001',
                task_type="retrieval_document",
                content=chunks
            )
            embeddings = response['embedding']
            document_embeddings_cache[document_id] = (chunks, embeddings)
            print(f"Embeddings cached for document {document_id} using fallback model")
            return chunks, embeddings
        except Exception as e2:
            print(f"Fallback embedding error: {e2}")
            document_embeddings_cache[document_id] = ([], [])
            return [], []


def find_relevant_chunks(user_query, doc_chunks, doc_embeddings):
    if not doc_chunks or not doc_embeddings:
        return ["(Document context not available)"]

    try:
        query_response = genai.embed_content(
            model='models/text-embedding-004',
            task_type="retrieval_query",
            content=user_query
        )
        query_embedding = query_response['embedding']
    except Exception:
        query_response = genai.embed_content(
            model='models/embedding-001',
            task_type="retrieval_query",
            content=user_query
        )
        query_embedding = query_response['embedding']
        
    try:
        dot_products = np.dot(doc_embeddings, query_embedding)
        norms = norm(doc_embeddings, axis=1) * norm(query_embedding)
        
        norms[norms == 0] = 1e-9
        
        similarities = dot_products / norms
        
        top_indices = np.argsort(similarities)[-3:][::-1]
        
        return [doc_chunks[i] for i in top_indices]
    except Exception as e:
        print(f"Error finding relevant chunks: {e}")
        return [f"(Error retrieving document context: {e})"]


def calculate_question_count(word_count):
    if word_count < 100:
        return 5
    elif word_count < 300:
        return 10
    elif word_count < 500:
        return 15
    elif word_count < 1000:
        return 20
    else:
        return min(50, (word_count // 100) * 2)

def get_prompt_template(language='en', difficulty='medium'):
    difficulty_instructions = {
        'easy': {
            'en': 'Focus on basic application and straightforward analysis. Questions should test fundamental understanding.',
            'bn': 'মৌলিক প্রয়োগ এবং সরল বিশ্লেষণে ফোকাস করুন। প্রশ্নগুলি মৌলিক বোঝাপড়া পরীক্ষা করবে।'
        },
        'medium': {
            'en': 'Require synthesis of multiple concepts and deeper evaluation. Balance between application and analysis.',
            'bn': 'একাধিক ধারণার সংশ্লেষণ এবং গভীর মূল্যায়ন প্রয়োজন। প্রয়োগ এবং বিশ্লেষণের মধ্যে ভারসাম্য।'
        },
        'hard': {
            'en': 'Demand complex evaluation, creation of solutions, and advanced critical thinking. Highly challenging questions.',
            'bn': 'জটিল মূল্যায়ন, সমাধান সৃষ্টি এবং উন্নত সমালোচনামূলক চিন্তাভাবনা প্রয়োজন। অত্যন্ত চ্যালেঞ্জিং প্রশ্ন।'
        }
    }
    
    prompts = {
        'en': f"""
You are an expert educator specialized in creating INFERENTIAL and CRITICAL THINKING questions.

DIFFICULTY LEVEL: {difficulty.upper()}
{difficulty_instructions[difficulty]['en']}

DOCUMENT CONTENT:
{{document_text}}

PREVIOUSLY GENERATED QUESTIONS (DO NOT REPEAT):
{{previous_questions}}

TASK: Generate 1 UNIQUE Multiple Choice Question (MCQ) that requires:
- Deep comprehension and analysis (NOT just fact recall)
- Connecting multiple concepts from the document
- Drawing logical conclusions
- Applying knowledge to new scenarios
- Understanding implicit meanings

COGNITIVE LEVELS TO USE (vary across questions):
- Apply: How would this concept work in situation X?
- Analyze: What's the relationship between A and B?
- Evaluate: Which approach would be most effective and why?
- Create: How could you combine these ideas to solve Y?

RULES:
1. NO direct fact-recall questions
2. Answer should NOT be explicitly stated in text
3. Require synthesis of multiple document parts
4. All 4 options must be plausible (no obviously wrong answers)
5. Question must test analytical/critical thinking
6. Ensure this question is DIFFERENT from all previous questions

OUTPUT FORMAT (JSON only):
{{{{
  "question": "The inferential question text",
  "options": {{{{
    "A": "Option 1",
    "B": "Option 2",
    "C": "Option 3",
    "D": "Option 4"
  }}}},
  "correct_answer": "A",
  "explanation": "Detailed explanation with reasoning",
  "cognitive_level": "Analyze"
}}}}

CRITICAL: Output ONLY valid JSON. No markdown, no extra text.
""",
        'bn': f"""
আপনি একজন বিশেষজ্ঞ শিক্ষাবিদ যিনি অনুমানমূলক এবং সমালোচনামূলক চিন্তাভাবনা প্রশ্ন তৈরিতে দক্ষ।

কঠিনতার স্তর: {difficulty.upper()}
{difficulty_instructions[difficulty]['bn']}

নথির বিষয়বস্তু:
{{document_text}}

পূর্বে তৈরি প্রশ্ন (পুনরাবৃত্তি করবেন না):
{{previous_questions}}

কাজ: ১টি অনন্য বহুনির্বাচনী প্রশ্ন (MCQ) তৈরি করুন যার জন্য প্রয়োজন:
- গভীর বোঝাপড়া এবং বিশ্লেষণ (শুধুমাত্র তথ্য মুখস্থ নয়)
- নথি থেকে একাধিক ধারণা সংযুক্ত করা
- যৌক্তিক সিদ্ধান্তে উপনীত হওয়া
- নতুন পরিস্থিতিতে জ্ঞান প্রয়োগ করা
- অন্তর্নিহিত অর্থ বোঝা

জ্ঞানীয় স্তর ব্যবহার করুন (প্রশ্ন জুড়ে বৈচিত্র্য):
- প্রয়োগ: এই ধারণাটি X পরিস্থিতিতে কীভাবে কাজ করবে?
- বিশ্লেষণ: A এবং B এর মধ্যে সম্পর্ক কী?
- মূল্যায়ন: কোন পদ্ধতি সবচেয়ে কার্যকর হবে এবং কেন?
- সৃষ্টি: Y সমাধানের জন্য এই ধারণাগুলি কীভাবে একত্রিত করবেন?

নিয়ম:
1. সরাসরি তথ্য-স্মরণ প্রশ্ন নয়
2. উত্তর পাঠ্যে স্পষ্টভাবে উল্লেখ করা উচিত নয়
3. নথির একাধিক অংশের সংশ্লেষণ প্রয়োজন
4. সব ৪টি বিকল্প যুক্তিসঙ্গত হতে হবে (স্পষ্টতই ভুল উত্তর নয়)
5. প্রশ্ন বিশ্লেষণাত্মক/সমালোচনামূলক চিন্তাভাবনা পরীক্ষা করবে
6. এই প্রশ্নটি পূর্বের সব প্রশ্ন থেকে আলাদা হতে হবে

আউটপুট ফর্ম্যাট (শুধুমাত্র JSON):
{{{{
  "question": "অনুমানমূলক প্রশ্নের টেক্সট",
  "options": {{{{
    "A": "বিকল্প ১",
    "B": "বিকল্প ২",
    "C": "বিকল্প ৩",
    "D": "বিকল্প ৪"
  }}}},
  "correct_answer": "A",
  "explanation": "যুক্তি সহ বিস্তারিত ব্যাখ্যা",
  "cognitive_level": "বিশ্লেষণ"
}}}}

গুরুত্বপূর্ণ: শুধুমাত্র বৈধ JSON আউটপুট করুন। কোন মার্কডাউন, অতিরিক্ত টেক্সট নয়।
"""
    }
    
    return prompts.get(language, prompts['en'])

def stream_questions(document_text, question_count, document_id, difficulty='medium', language='en'):
    previous_questions = db.get_questions_by_document(document_id)
    previous_q_texts = [q['question_text'] for q in previous_questions]
    
    prompt_template = get_prompt_template(language, difficulty)
    
    generated_count = 0
    max_retries = 5 
    retries = 0
    
    while generated_count < question_count:
        
        if retries >= max_retries:
            print(f"Max retries reached for doc {document_id}. Stopping generation.")
            error_message = json.dumps({
                'error': f"Failed to generate questions after {max_retries} attempts. Please check API key or network.",
                'status': 'failed'
            })
            yield f"data: {error_message}\n\n"
            break 

        recent_previous_q_texts = previous_q_texts[-5:]
        
        prompt = prompt_template.format(
            document_text=document_text,
            previous_questions='\n'.join(recent_previous_q_texts) if recent_previous_q_texts else 'None'
        )
        
        try:
            response = generation_model.generate_content(prompt)
            response_text = response.text.strip()
            
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise Exception("No JSON found in response")
                
            response_text = response_text[json_start:json_end]
            
            question_data = json.loads(response_text)
            
            if not all(k in question_data for k in ['question', 'options', 'correct_answer', 'explanation']):
                 raise Exception("Incomplete JSON response from model")
            
            question_hash = hashlib.md5(
                question_data['question'].encode('utf-8')
            ).hexdigest()
            
            if not db.question_exists(document_id, question_hash):
                db_question_id = db.save_question(document_id, question_data, question_hash)
                
                if db_question_id:
                    previous_q_texts.append(question_data['question'])
                    question_data['id'] = db_question_id
                    generated_count += 1
                    retries = 0 
                    yield f"data: {json.dumps(question_data, ensure_ascii=False)}\n\n"
            else:
                print("Duplicate question skipped.")
                retries += 1 
                continue
                
        except Exception as e:
            print(f"Error generating question {generated_count}: {e}")
            print(f"Problematic response text: {response_text}")
            retries += 1 
            error_message = json.dumps({
                'error': f"Failed to generate question {generated_count+1}", 
                'details': "AI response was not valid JSON or generation failed.",
                'status': 'retrying'
            })
            yield f"data: {error_message}\n\n"
            time.sleep(1) 
            continue
        
        time.sleep(0.5)

    print(f"Finished generating {generated_count} questions for doc {document_id}")
    yield f"data: {json.dumps({'status': 'done'})}\n\n"

@app.route('/api/upload', methods=['POST'])
def upload_document():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        language = request.form.get('language', 'en')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        text_content = doc_processor.extract_text(file)
        
        if not text_content:
            return jsonify({'error': 'Could not extract text from document'}), 400
        
        content_hash = hashlib.md5(text_content.encode('utf-8')).hexdigest()
        
        word_count = len(text_content.split())
        
        document_id = db.save_document(
            filename=file.filename,
            content=text_content,
            content_hash=content_hash,
            word_count=word_count, 
            language=language
        )
        
        try:
            get_or_create_document_embeddings(document_id, text_content)
        except Exception as e:
            print(f"Warning: Failed to pre-cache embeddings for doc {document_id}: {e}")
        
        return jsonify({
            'document_id': document_id,
            'content_preview': text_content[:200] + '...',
            'filename': file.filename
        })
        
    except Exception as e:
        print(f"Error in upload: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-questions/<int:document_id>', methods=['GET'])
def generate_questions(document_id):
    try:
        document = db.get_document(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        question_count = request.args.get('count', type=int)
        difficulty = request.args.get('difficulty', default='medium')
        language = request.args.get('language', default=document.get('language', 'en'))
        
        if not question_count:
            question_count = 10 
            
        if question_count < 1 or question_count > 50:
            question_count = min(50, max(1, question_count))
        
        if difficulty not in ['easy', 'medium', 'hard']:
            difficulty = 'medium'
            
        if language not in ['en', 'bn']:
            language = 'en'
        
        return Response(
            stream_questions(
                document['content'], 
                question_count, 
                document_id,
                difficulty,
                language
            ),
            mimetype='text/event-stream; charset=utf-8',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )
        
    except Exception as e:
        print(f"Error in generate-questions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/start', methods=['POST'])
def start_session():
    try:
        data = request.json
        document_id = data.get('document_id')
        total_questions = data.get('total_questions')

        if not document_id or not total_questions:
            return jsonify({'error': 'Missing document_id or total_questions'}), 400

        session_id = db.start_session(document_id, total_questions)
        return jsonify({'session_id': session_id})
    except Exception as e:
        print(f"Error starting session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-answers', methods=['POST'])
def submit_answers():
    try:
        data = request.json
        document_id = data.get('document_id')
        session_id = data.get('session_id')
        user_answers = data.get('answers')
        
        if not document_id or not user_answers or not session_id:
            return jsonify({'error': 'Missing required data (document_id, session_id, answers)'}), 400
        
        questions = db.get_questions_by_document(document_id)
        
        if not questions:
            return jsonify({'error': 'No questions found'}), 404
        
        question_map = {str(q['id']): q for q in questions}
        
        results = {
            'total': len(questions),
            'correct': 0,
            'wrong': [],
            'all_correct': True
        }
        
        for question_id_str, user_answer in user_answers.items():
            if question_id_str in question_map:
                question = question_map[question_id_str]
                correct_answer = question['correct_answer']
                
                is_correct = (user_answer == correct_answer)
                db.save_attempt(session_id, question['id'], user_answer, is_correct)
                
                if is_correct:
                    results['correct'] += 1
                else:
                    results['all_correct'] = False
                    results['wrong'].append({
                        'question_id': question['id'],
                        'question': question['question_text'],
                        'options': question['options'],
                        'user_answer': user_answer or 'No answer provided',
                        'correct_answer': correct_answer,
                        'explanation': question['explanation']
                    })
            else:
                print(f"Warning: Answer submitted for unknown question ID {question_id_str}")

        answered_question_ids = set(user_answers.keys())
        for q_id_str, question in question_map.items():
            if q_id_str not in answered_question_ids:
                results['all_correct'] = False
                db.save_attempt(session_id, question['id'], None, False)
                results['wrong'].append({
                    'question_id': question['id'],
                    'question': question['question_text'],
                    'options': question['options'],
                    'user_answer': 'No answer provided',
                    'correct_answer': question['correct_answer'],
                    'explanation': question['explanation']
                })

        db.end_session(session_id, results['correct'])
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Error in submit_answers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    try:
        data = request.json
        document_id = data.get('document_id')
        user_message = data.get('message')
        chat_history = data.get('history', [])
        wrong_questions = data.get('wrong_questions', [])
        language = data.get('language', 'en')
        
        if not document_id or not user_message:
            return jsonify({'error': 'Missing required data'}), 400
        
        document = db.get_document(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        doc_chunks, doc_embeddings = get_or_create_document_embeddings(
            document_id, document['content']
        )
        
        relevant_chunks = find_relevant_chunks(
            user_message, doc_chunks, doc_embeddings
        )
        context_from_document = "\n\n---\n\n".join(relevant_chunks)

        tutor_instructions = {
            'en': """
You are a helpful tutor. The student has read a document and taken an MCQ test on it.
Your answers MUST be in English.

RELEVANT DOCUMENT EXCERPTS (Use this context to answer):
{context_from_document} 

{wrong_section}

CHAT HISTORY (Only last 10 messages):
{history}

STUDENT'S CURRENT MESSAGE: {message}

INSTRUCTIONS:
- Be encouraging and supportive
- Help the student learn from their mistakes
- Guide them to think deeply and critically
- Connect concepts back to the relevant document excerpts
- Explain in clear, simple language
- Ask thought-provoking follow-up questions when appropriate

Respond naturally and conversationally in English.
""",
            'bn': """
আপনি একজন সহায়ক শিক্ষক। শিক্ষার্থী একটি নথি পড়েছে এবং তার উপর MCQ পরীক্ষা দিয়েছে।
আপনার উত্তর অবশ্যই বাংলায় দিতে হবে।

প্রাসঙ্গিক নথি থেকে অংশ (উত্তর দিতে এই কনটেক্সট ব্যবহার করুন):
{context_from_document} 

{wrong_section}

চ্যাট ইতিহাস (শুধুমাত্র শেষ ১০টি বার্তা):
{history}

শিক্ষার্থীর বর্তমান বার্তা: {message}

নির্দেশনা:
- উৎসাহজনক এবং সহায়ক হন
- শিক্ষার্থীকে তাদের ভুল থেকে শিখতে সাহায্য করুন
- তাদের গভীরভাবে এবং সমালোচনামূলকভাবে চিন্তা করতে গাইড করুন
- ধারণাগুলি প্রাসঙ্গিক নথির অংশে ফিরিয়ে সংযুক্ত করুন
- স্পষ্ট, সহজ ভাষায় ব্যাখ্যা করুন
- উপযুক্ত হলে চিন্তা-উদ্দীপক ফলো-আপ প্রশ্ন জিজ্ঞাসা করুন

স্বাভাবিক এবং কথোপকথনমূলকভাবে বাংলায় প্রতিক্রিয়া জানান।
"""
        }
        
        wrong_section = ""
        if wrong_questions:
            wrong_labels = {
                'en': "Questions the student got wrong:",
                'bn': "শিক্ষার্থী যে প্রশ্নগুলি ভুল করেছে:"
            }
            wrong_section = wrong_labels.get(language, wrong_labels['en']) + "\n"
            for wq in wrong_questions:
                wrong_section += f"- {wq['question']}\n"
                correct_label = {'en': 'Correct answer:', 'bn': 'সঠিক উত্তর:'}
                explanation_label = {'en': 'Explanation:', 'bn': 'ব্যাখ্যা:'}
                wrong_section += f"  {correct_label.get(language, 'Correct answer:')} {wq['correct_answer']}\n"
                wrong_section += f"  {explanation_label.get(language, 'Explanation:')} {wq['explanation']}\n\n"
        
        history_text = ""
        role_labels = {
            'en': {'user': 'Student', 'assistant': 'Tutor'},
            'bn': {'user': 'শিক্ষার্থী', 'assistant': 'শিক্ষক'}
        }
        labels = role_labels.get(language, role_labels['en'])
        
        recent_history = chat_history[-10:] 
        for msg in recent_history:
            role = labels.get(msg['role'], msg['role'])
            history_text += f"{role}: {msg['content']}\n"
        
        template = tutor_instructions.get(language, tutor_instructions['en'])
        
        context = template.format(
            context_from_document=context_from_document,
            wrong_section=wrong_section,
            history=history_text,
            message=user_message
        )
        
        response = generation_model.generate_content(context)
        ai_response = response.text.strip()
        
        return jsonify({'response': ai_response})
        
    except Exception as e:
        print(f"Error in chat: {e}")
        return jsonify({'error': 'Failed to generate response'}), 500

@app.route('/api/statistics/<int:document_id>', methods=['GET'])
def get_statistics(document_id):
    try:
        stats = db.get_document_statistics(document_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/history', methods=['GET'])
def get_session_history():
    try:
        history = db.get_session_history()
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    try:
        analytics = db.get_overall_analytics()
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@app.route('/api/session/<int:session_id>', methods=['GET'])
def get_session_details_route(session_id):
    try:
        session_data = db.get_session_details(session_id)
        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        return jsonify(session_data)
    except Exception as e:
        print(f"Error in session details route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<int:session_id>', methods=['DELETE'])
def delete_session_route(session_id):
    try:
        success = db.delete_session(session_id)
        if not success:
            return jsonify({'error': 'Session not found or already deleted'}), 404
        return jsonify({'message': 'Session deleted successfully'})
    except Exception as e:
        print(f"Error in session delete route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'AI Study Assistant API is running'})

if __name__ == '__main__':
    print("Starting AI Study Assistant API...")
    print("Server running on http://localhost:5000")
    app.run(debug=True, port=5000, threaded=True)