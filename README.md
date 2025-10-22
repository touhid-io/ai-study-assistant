<h1 align="center">🤖 AI Study Assistant</h1>
<p align="center"><strong>Transform any document into an interactive quiz and chat session.</strong></p>
<p align="center">
This is an open-source prototype that uses the Google Gemini API to automatically generate critical-thinking MCQs and enable document-aware chat from your uploaded files (PDF, DOCX, TXT).
</p>
<p align="center">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/Python-3.9%2B-blue%3Flogo%3Dpython" alt="Python">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/Flask-black%3Flogo%3Dflask" alt="Flask">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/Google_Gemini-blueviolet%3Flogo%3Dgoogle" alt="Gemini">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/JavaScript-ES6-yellow%3Flogo%3Djavascript" alt="JavaScript">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/SQLite-blue%3Flogo%3Dsqlite" alt="SQLite">
</p>

🌟 Overview

This tool is a first step towards revolutionizing the learning process. It converts static text files into dynamic, interactive learning materials [cite: app.py]. Users can upload their notes, book chapters, or any text document, and the system instantly generates quizzes designed to stimulate critical thinking, not just rote memorization [cite: app.py].

🌱 The Vision: From Prototype to AI Super-Tutor

This project is the foundational prototype (MVP) for a much larger ambition: to build an AI-driven learning system that transcends traditional educational methods.

My ultimate goal is to create a system where:

• Knowledge Agents: Users' academic texts or books are transformed into multimodal chat sessions. Each uploaded book will create a distinct 'Knowledge Agent'.

• "Talk Active Book Interface": The core of the system will be real-time voice conversation. I plan to use fine-tuned open-source TTS models (like XTTS-v2 or ChatTTS) for low-latency, expressive human-like-tone conversations.

• Advanced RAG Architecture: The system's nucleus will be a fine-tuned LLM (like Llama 3 or Mixtral 8x22B). It won't just repeat information but will generate answers by analyzing the uploaded book's database and cross-domain PhD-level research papers using a Retrieval Augmented Generation (RAG) architecture.

• On-the-fly Visualization Canvas: When a student wants to understand a complex or abstract concept, the system will use a fine-tuned image generation model (like Stable Diffusion or Qwen-Image) to instantly convert that abstract concept into an accurately labeled diagram, graph, or simulation visual.

• Dynamic Assessment: Like this prototype, but far more advanced, using algorithms to generate open-ended and critical-thinking questions.

This current project is the first block in building an AI tutor that has the potential to surpass the knowledge of a collective of human experts.

✨ Key Features (of this Prototype)

• Multi-Format Support: Extracts text from .pdf, .docx, .txt, and .md files [cite: document_processor.py].

• Dynamic MCQ Generation: Uses the Google Gemini API to instantly generate Multiple Choice Questions from any text [cite: app.py].

• Adjustable Difficulty: Allows users to select 'Easy', 'Medium', or 'Hard' difficulty for the generated questions [cite: app.py].

• Interactive Quiz UI: A clean, user-friendly interface to answer questions and receive immediate feedback [cite: index.html].

• Review & Explanation: After the quiz, users can review their incorrect answers with detailed explanations provided by the AI [cite: script.js].

• AI Tutor (Chat): A RAG-based chatbot that allows users to ask questions specifically about the uploaded document [cite: app.py].

• Session History: Uses an SQLite database to save previous quiz sessions and track performance over time [cite: database.py, script.js].

🏗️ Architecture (Current Prototype)

This project runs on a simple client-server model.

┌──────────────────┐       ┌────────────────────────┐       ┌────────────────┐
│   Frontend       │──────▶│   Flask Backend        │──────▶│ Google Gemini  │
│ (HTML, CSS, JS)  │◀──────│   (Python / app.py)    │◀──────│ (MCQ Gen & Chat)│
└──────────────────┘       └────────────────────────┘       └────────────────┘
                             │         │         │
                             │         │         ▼
                             │         │     ┌───────────┐
                             │         └────▶│ Embeddings│
                             │               └───────────┘
                             ▼
                     ┌────────────────┐
                     │  SQLite DB     │
                     │ (Sessions, Qs) │
                     └────────────────┘


Tech Stack:

• Backend: Flask (Python), Gunicorn [cite: app.py, requirements.txt]

• AI: Google Generative AI (Gemini Flash/Pro), NumPy [cite: app.py, requirements.txt]

• Frontend: Vanilla JavaScript, HTML5, CSS3 [cite: index.html, script.js, style.css]

• Database: SQLite [cite: database.py]

• Text Extraction: PyPDF2, python-docx [cite: document_processor.py, requirements.txt]

🚀 Getting Started (How to Run Locally)

This is the most important part for open-source users. Follow these steps to run the project on your own machine.

Prerequisites

• Python 3.9+

• Google Gemini API Key: You will need your own API key. You can get one for free from Google AI Studio.

Installation & Setup

1. Clone the Repository:

git clone [https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git)
cd YOUR_REPOSITORY_NAME


2. Set up the Backend:
Navigate to the backend folder and install the required packages.

cd backend
pip install -r requirements.txt


3. Configure Environment (CRITICAL):
You must create a .env file inside the backend folder.

Create the file:

# Inside the 'backend' folder
touch .env


Open the .env file and add your Gemini API Key like this:

GEMINI_API_KEY=YOUR_OWN_API_KEY_GOES_HERE


(The provided .gitignore file will prevent this file from ever being uploaded to GitHub).

4. Run the Backend Server:
While still in the backend folder, run the app:

python app.py


The server will start running at http://localhost:5000 [cite: app.py].

5. Launch the Frontend:
Navigate to the frontend folder and simply open the index.html file in your web browser.

cd ../frontend
# On Windows
start index.html
# On macOS
open index.html
# On Linux
xdg-open index.html


The frontend will automatically connect to your backend running on localhost:5000 [cite: script.js].

📖 How to Use

1. Upload Document: Upload your .pdf, .docx, or .txt file [cite: document_processor.py].

2. Set Options: Choose the number of questions and the difficulty level [cite: script.js].

3. Generate Quiz: The AI will read your document and create a set of questions [cite: app.py].

4. Take Quiz: Answer the questions in the interactive UI.

5. Review: See your score, review incorrect answers, and read the explanations [cite: script.js].

6. Chat: Click "Discuss with AI" to ask any follow-up questions about the document content [cite: app.py].

🤝 Contributing

This is an open-source project and a prototype. Contributions are highly welcome! Feel free to open a Pull Request, report bugs, or suggest new features.

<p align="center">
<sub>If you find this project interesting, please consider giving it a star ⭐!</sub>
</p>