const state = {
    currentView: 'upload',
    currentStep: 'upload',
    theme: 'dark',
    language: 'en',
    sessionId: null,
    file: null,
    documentId: null,
    documentInfo: null,
    questions: [],
    userAnswers: {},
    bookmarkedQuestions: new Set(),
    results: null,
    chatMessages: [],
    sessions: [],
    settings: {
        questionCount: 10,
        difficulty: 'medium',
        questionType: 'mcq',
        timer: 0
    },
    timer: {
        started: null,
        elapsed: 0,
        interval: null
    }
};

const API_URL = 'http://localhost:5000/api';

const translations = {
    en: {
        upload: 'Upload Your Document',
        generate: 'Generate Questions',
        submit: 'Submit All Answers',
        discuss: 'Discuss with AI',
        newSession: 'New Session'
    },
    bn: {
        upload: 'আপনার ডকুমেন্ট আপলোড করুন',
        generate: 'প্রশ্ন তৈরি করুন',
        submit: 'সব উত্তর জমা দিন',
        discuss: 'AI এর সাথে আলোচনা করুন',
        newSession: 'নতুন সেশন'
    }
};

document.addEventListener('DOMContentLoaded', () => {
    loadStateFromStorage();
    setupEventListeners();
    renderUI();
});

function loadStateFromStorage() {
    const saved = localStorage.getItem('studyai_state');
    if (saved) {
        try {
            const parsed = JSON.parse(saved);
            Object.assign(state, parsed);
            state.bookmarkedQuestions = new Set(parsed.bookmarkedQuestions || []);
        } catch (e) {
            console.error('Failed to load state:', e);
        }
    }
    
    const theme = localStorage.getItem('studyai_theme') || 'dark';
    setTheme(theme);
}

function saveState() {
    const toSave = {
        ...state,
        file: null,
        bookmarkedQuestions: Array.from(state.bookmarkedQuestions)
    };
    localStorage.setItem('studyai_state', JSON.stringify(toSave));
}

function toggleTheme() {
    const newTheme = state.theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

function setTheme(theme) {
    state.theme = theme;
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('studyai_theme', theme);
    
    const icon = document.getElementById('theme-icon');
    if (theme === 'dark') {
        icon.innerHTML = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
    } else {
        icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
    }
}

document.getElementById('language-select').addEventListener('change', (e) => {
    state.language = e.target.value;
    saveState();
    updateLanguage();
});

function updateLanguage() {
    const t = translations[state.language];
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`${viewName}-view`).classList.add('active');
    state.currentView = viewName;
    
    updateStepper(viewName);
    saveState();
}

function updateStepper(currentStep) {
    const steps = ['upload', 'generating', 'answering', 'results'];
    const currentIndex = steps.indexOf(currentStep);
    
    document.querySelectorAll('.step').forEach((step, index) => {
        step.classList.remove('active', 'completed');
        if (index < currentIndex) {
            step.classList.add('completed');
        } else if (index === currentIndex) {
            step.classList.add('active');
        }
    });
}

function goHome() {
    showView('upload');
}

function setupEventListeners() {
    const dropZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    
    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    uploadBtn.addEventListener('click', uploadFile);
    
    document.getElementById('question-count').addEventListener('input', (e) => {
        document.getElementById('question-count-display').textContent = e.target.value;
        state.settings.questionCount = parseInt(e.target.value);
        saveState();
    });
    
    document.getElementById('timer-setting').addEventListener('input', (e) => {
        const value = parseInt(e.target.value);
        state.settings.timer = value;
        document.getElementById('timer-display').textContent = value === 0 ? 'No time limit' : `${value} minutes`;
        saveState();
    });
    
    document.querySelectorAll('.difficulty-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const parent = e.target.parentElement;
            parent.querySelectorAll('.difficulty-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            if (e.target.dataset.difficulty) {
                state.settings.difficulty = e.target.dataset.difficulty;
            }
            if (e.target.dataset.type) {
                state.settings.questionType = e.target.dataset.type;
            }
            saveState();
        });
    });
    
    document.getElementById('submit-btn').addEventListener('click', submitAnswers);
    
    document.getElementById('chat-send-btn').addEventListener('click', sendChatMessage);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
    
    document.addEventListener('keydown', handleKeyboardShortcut);

    document.getElementById('logo').addEventListener('click', goHome);
    document.getElementById('theme-toggle-btn').addEventListener('click', toggleTheme);
    document.getElementById('sidebar-toggle-btn').addEventListener('click', toggleSidebar);

    document.getElementById('nav-settings-btn').addEventListener('click', () => showView('settings'));
    document.getElementById('nav-analytics-btn').addEventListener('click', () => showView('analytics'));
    document.getElementById('nav-help-btn').addEventListener('click', showHelp);

    document.getElementById('back-to-upload-btn').addEventListener('click', () => showView('upload'));
    document.getElementById('save-exit-btn').addEventListener('click', saveAndExit);
    
    document.getElementById('discuss-ai-btn').addEventListener('click', () => showView('discussion'));
    document.getElementById('retry-btn').addEventListener('click', retryQuiz);
    document.getElementById('new-session-btn').addEventListener('click', newSession);
    
    document.getElementById('export-chat-btn').addEventListener('click', exportChat);
    document.getElementById('back-to-results-btn').addEventListener('click', () => showView('results'));
    document.getElementById('analytics-back-btn').addEventListener('click', () => showView('upload'));

    document.getElementById('start-generation-btn').addEventListener('click', () => {
        showView('upload');
    });

    document.getElementById('preview-questions-btn').addEventListener('click', () => {
        startNewSession();
    });

    document.getElementById('question-list').addEventListener('click', (e) => {
        const bookmarkBtn = e.target.closest('.bookmark-btn');
        if (bookmarkBtn) {
            const qId = bookmarkBtn.dataset.questionId;
            toggleBookmark(qId);
        }
    });

    document.getElementById('chat-messages').addEventListener('click', (e) => {
        const copyBtn = e.target.closest('.copy-btn');
        if (copyBtn) {
            const content = copyBtn.dataset.messageContent;
            copyMessage(content);
        }
    });

    document.getElementById('active-session-container').addEventListener('click', (e) => {
        if (e.target.id === 'resume-session-btn') {
            resumeSession();
        }
        if (e.target.id === 'save-exit-sidebar-btn') {
            saveAndExit();
        }
    });

    document.getElementById('session-history').addEventListener('click', (e) => {
        const deleteBtn = e.target.closest('.delete-session-btn');
        const card = e.target.closest('.session-card');

        if (deleteBtn) {
            e.stopPropagation(); 
            if (confirm('Are you sure you want to delete this session?')) {
                deleteSession(deleteBtn.dataset.sessionId);
            }
        } else if (card && card.dataset.sessionId) {
            if (!e.target.closest('.delete-session-btn')) {
                 loadSessionResults(card.dataset.sessionId);
            }
        }
    });
}

function handleFileSelect(file) {
    state.file = file;
    document.getElementById('file-name').textContent = file.name;
    document.getElementById('upload-btn').disabled = false;
    saveState();
}

async function uploadFile() {
    if (!state.file) return;
    
    const btn = document.getElementById('upload-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="loader"></div><span>Processing...</span>';
    
    const formData = new FormData();
    formData.append('file', state.file);
    formData.append('language', state.language);
    
    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Upload failed');
        
        const data = await response.json();
        state.documentId = data.document_id;
        state.documentInfo = data; 

        saveState();
        document.getElementById('start-generation-btn').disabled = false;
        startQuestionGeneration(); 

    } catch (error) {
        document.getElementById('upload-error').textContent = error.message;
        document.getElementById('upload-error').style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>Upload & Generate</span>';
    }
}

function startQuestionGeneration() {
    if (!state.documentInfo || !state.documentId) {
        alert('Please upload a document first.');
        showView('upload');
        return;
    }
    
    state.questions = [];
    showView('generating');

    document.getElementById('generating-loader-content').style.display = 'block';
    document.getElementById('generating-success-content').style.display = 'none';
    document.getElementById('preview-questions-btn').style.display = 'none';
    document.getElementById('generating-status').textContent = 'Analyzing Document...';

    document.getElementById('generating-info').textContent = 
        `Document: ${state.documentInfo.filename} • Generating ${state.settings.questionCount} questions`;
    
    const listEl = document.getElementById('generated-questions-list');
    listEl.innerHTML = '';
    
    let sessionStarted = false; 

    const eventSource = new EventSource(`${API_URL}/generate-questions/${state.documentId}?count=${state.settings.questionCount}&difficulty=${state.settings.difficulty}&language=${state.language}`);
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.status === 'done') {
            eventSource.close(); 
            if (!sessionStarted) { 
                sessionStarted = true;
                if (state.questions.length > 0) {
                    showGenerationSuccess();
                } else {
                    alert('Generation finished, but no questions were created.');
                    showView('upload');
                }
            }
            return; 
        }

        if (data.error) {
            console.error("Error from stream:", data.details);
            alert(`An error occurred: ${data.details}`);
            eventSource.close();
            sessionStarted = true;
            showView('upload');
            return;
        }

        const question = data;
        state.questions.push(question);
        
        const item = document.createElement('div');
        item.className = 'session-card';
        item.style.animation = 'slideIn 0.3s ease-out';
        item.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                <div>
                    <div style="font-weight: 600;">Question ${state.questions.length}</div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">${question.question.substring(0, 60)}...</div>
                </div>
            </div>
        `;
        listEl.appendChild(item);
        listEl.scrollTop = listEl.scrollHeight;
    };
    
    eventSource.onerror = () => {
        eventSource.close();
        
        if (sessionStarted) return; 
        sessionStarted = true;

        if (state.questions.length > 0) {
            showGenerationSuccess();
        } else {
            alert('Failed to generate questions. Stream connection error.');
            showView('upload');
        }
    };
}

function showGenerationSuccess() {
    document.getElementById('generating-loader-content').style.display = 'none';
    
    const successContent = document.getElementById('generating-success-content');
    successContent.style.display = 'block';
    
    document.getElementById('generating-success-status').textContent = 'Generation Complete!';
    document.getElementById('generating-success-info').textContent = 
        `${state.questions.length} questions have been successfully generated.`;
        
    document.getElementById('preview-questions-btn').style.display = 'block';
}

async function startNewSession() {
    try {
        const response = await fetch(`${API_URL}/session/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id: state.documentId,
                total_questions: state.questions.length
            })
        });
        if (!response.ok) throw new Error('Failed to start session');
        
        const data = await response.json();
        state.sessionId = data.session_id;
        
        saveState();
        renderQuestions(); 

    } catch (error) {
        console.error(error);
        alert('Could not start a new session. Please try again.');
        showView('upload');
    }
}

function renderQuestions() {
    showView('answering');
    
    const container = document.getElementById('question-list');
    container.innerHTML = '';
    
    state.questions.forEach((q, index) => {
        const card = document.createElement('div');
        card.className = 'question-card';
        card.id = `question-${index}`;
        
        const optionsHTML = Object.entries(q.options).map(([key, value]) => {
            const isSelected = state.userAnswers[q.id] === key;
            return `
                <label class="option ${isSelected ? 'selected' : ''}">
                    <input type="radio" name="q_${q.id}" value="${key}" ${isSelected ? 'checked' : ''}>
                    <span><strong>${key}.</strong> ${value}</span>
                </label>
            `;
        }).join('');
        
        const isBookmarked = state.bookmarkedQuestions.has(q.id);
        
        card.innerHTML = `
            <div class="question-header">
                <div style="display: flex; align-items: flex-start; gap: 1rem; flex: 1;">
                    <div class="question-number">${index + 1}</div>
                    <div class="question-text">${q.question}</div>
                </div>
                <div class="question-actions">
                    <button class="action-btn bookmark-btn ${isBookmarked ? 'active' : ''}" data-question-id="${q.id}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="${isBookmarked ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" style="pointer-events: none;">
                            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="options">${optionsHTML}</div>
        `;
        
        container.appendChild(card);
    });
    
    container.addEventListener('change', (e) => {
        if (e.target.type === 'radio') {
            const qId = e.target.name.replace('q_', '');
            state.userAnswers[qId] = e.target.value;
            
            e.target.closest('.question-card').querySelectorAll('.option').forEach(o => o.classList.remove('selected'));
            e.target.closest('.option').classList.add('selected');
            
            updateAnsweredCount();
            saveState();
        }
    });
    
    updateAnsweredCount();
    
    if (state.settings.timer > 0) {
        startTimer();
    }
}

function updateAnsweredCount() {
    const answered = Object.keys(state.userAnswers).length;
    const total = state.questions.length;
    document.getElementById('answered-count').textContent = `${answered}/${total} answered`;
    document.getElementById('submit-btn').disabled = answered !== total;
}

function toggleBookmark(questionId) {
    if (state.bookmarkedQuestions.has(questionId)) {
        state.bookmarkedQuestions.delete(questionId);
    } else {
        state.bookmarkedQuestions.add(questionId);
    }
    const btn = document.querySelector(`.bookmark-btn[data-question-id="${questionId}"]`);
    if (btn) {
        btn.classList.toggle('active');
        const svg = btn.querySelector('svg');
        svg.setAttribute('fill', btn.classList.contains('active') ? 'currentColor' : 'none');
    }
    saveState();
}

function startTimer() {
    state.timer.started = Date.now();
    const timerDisplay = document.getElementById('timer-display-active');
    timerDisplay.style.display = 'block';
    
    const totalSeconds = state.settings.timer * 60;
    
    state.timer.interval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - state.timer.started) / 1000);
        const remaining = totalSeconds - elapsed;
        
        if (remaining <= 0) {
            clearInterval(state.timer.interval);
            submitAnswers();
            return;
        }
        
        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;
        timerDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        if (remaining <= 60) {
            timerDisplay.style.background = 'var(--error)';
            timerDisplay.style.color = 'white';
        }
    }, 1000);
}

async function submitAnswers() {
    if (state.timer.interval) {
        clearInterval(state.timer.interval);
        state.timer.elapsed = Math.floor((Date.now() - state.timer.started) / 1000);
    }
    
    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="loader"></div><span>Submitting...</span>';
    
    try {
        const response = await fetch(`${API_URL}/submit-answers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id: state.documentId,
                session_id: state.sessionId,
                answers: state.userAnswers
            })
        });
        
        if (!response.ok) throw new Error('Submission failed');
        
        state.results = await response.json();
        state.results.timeTaken = state.timer.elapsed;
        
        renderResults();
        saveState();

        renderSessionHistory();
        updateAnalytics();

    } catch (error) {
        alert('Failed to submit answers: ' + error.message);
        btn.disabled = false;
        btn.innerHTML = '<span>Submit All Answers</span>';
    }
}

function renderResults() {
    showView('results');
    
    const { correct, total, wrong } = state.results;
    const percentage = Math.round((correct / total) * 100);
    
    document.getElementById('result-score').textContent = `${correct}/${total}`;
    document.getElementById('stat-correct').textContent = correct;
    document.getElementById('stat-wrong').textContent = wrong.length;
    document.getElementById('stat-percentage').textContent = `${percentage}%`;
    
    const timeToDisplay = state.results.timeTaken || state.timer.elapsed;
    const minutes = Math.floor(timeToDisplay / 60);
    const seconds = timeToDisplay % 60;
    document.getElementById('stat-time').textContent = `${minutes}m ${seconds}s`;
    
    if (correct === total) {
        document.getElementById('result-title').textContent = '🎉 Perfect Score!';
        document.getElementById('result-message').textContent = 'Excellent! You answered all questions correctly!';
        createConfetti();
    } else if (percentage >= 80) {
        document.getElementById('result-title').textContent = '🌟 Great Job!';
        document.getElementById('result-message').textContent = `You scored ${percentage}%! Keep up the good work!`;
    } else if (percentage >= 60) {
        document.getElementById('result-title').textContent = '👍 Good Effort!';
        document.getElementById('result-message').textContent = `You scored ${percentage}%. Review the incorrect answers to improve.`;
    } else {
        document.getElementById('result-title').textContent = '📚 Keep Learning!';
        document.getElementById('result-message').textContent = `You scored ${percentage}%. Don't worry, practice makes perfect!`;
    }
    
    const incorrectSection = document.getElementById('incorrect-answers-section');
    if (wrong.length > 0) {
        incorrectSection.innerHTML = '<h3 style="margin: 2rem 0 1rem;">Review Incorrect Answers</h3>';
        wrong.forEach((w, index) => {
            const card = document.createElement('div');
            card.className = 'question-card';
            card.style.borderColor = 'var(--error)';
            card.innerHTML = `
                <div class="question-header">
                    <div class="question-number" style="background: var(--error);">${index + 1}</div>
                    <div class="question-text">${w.question}</div>
                </div>
                <div style="margin-left: 3rem;">
                    <p style="margin: 0.5rem 0; color: var(--error);">
                        <strong>Your Answer:</strong> ${w.user_answer || 'No answer'}
                    </p>
                    <p style="margin: 0.5rem 0; color: var(--success);">
                        <strong>Correct Answer:</strong> ${w.correct_answer}
                    </p>
                    <p style="margin: 0.5rem 0; padding: 1rem; background: var(--bg-tertiary); border-radius: 0.5rem;">
                        <strong>Explanation:</strong> ${w.explanation}
                    </p>
                </div>
            `;
            incorrectSection.appendChild(card);
        });
    } else {
        incorrectSection.innerHTML = '';
    }
}

function createConfetti() {
    const colors = ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'];
    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + '%';
            confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.animationDelay = Math.random() * 0.5 + 's';
            document.body.appendChild(confetti);
            setTimeout(() => confetti.remove(), 3000);
        }, i * 50);
    }
}

async function renderSessionHistory() {
    const container = document.getElementById('session-history');
    container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.875rem;">Loading history...</p>';

    try {
        const response = await fetch(`${API_URL}/session/history`);
        if (!response.ok) throw new Error('Failed to load history');
        
        const sessions = await response.json();
        
        if (sessions.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.875rem;">No previous sessions</p>';
            return;
        }

        container.innerHTML = sessions.map(session => {
            const date = new Date(session.date);
            const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            return `
                <div class="session-card" data-session-id="${session.id}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div class="session-title" style="cursor: pointer;">${session.fileName}</div>
                        <button class="action-btn delete-session-btn" data-session-id="${session.id}" style="width: 28px; height: 28px; background: rgba(239, 68, 68, 0.1); color: var(--error);">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events: none;">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                    </div>
                    <div class="session-meta">${dateStr}</div>
                    <div class="session-meta">Score: ${session.score}/${session.total} (${session.percentage}%)</div>
                    <div class="session-progress">
                        <div class="session-progress-bar" style="width: ${session.percentage}%"></div>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error(error);
        container.innerHTML = '<p style="color: var(--error); font-size: 0.875rem;">Could not load history</p>';
    }
}

function renderActiveSession() {
    const container = document.getElementById('active-session-container');
    if (!state.documentId) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.875rem;">No active session</p>';
        return;
    }
    
    const answered = Object.keys(state.userAnswers).length;
    const total = state.questions.length;
    const progress = total > 0 ? Math.round((answered / total) * 100) : 0;
    
    container.innerHTML = `
        <div class="session-card active">
            <div class="session-header">
                <div class="session-status"></div>
                <span style="font-size: 0.75rem; color: white;">ACTIVE</span>
            </div>
            <div class="session-title">${state.documentInfo?.filename || 'Current Session'}</div>
            <div class="session-meta">Progress: ${answered}/${total} answered</div>
            <div class="session-progress">
                <div class="session-progress-bar" style="width: ${progress}%"></div>
            </div>
            <div class="session-actions">
                <button class="session-btn" id="resume-session-btn">Resume</button>
                <button class="session-btn" id="save-exit-sidebar-btn">Save & Exit</button>
            </div>
        </div>
    `;
}

function resumeSession() {
    if (state.questions.length > 0) {
        renderQuestions();
    } else {
        showView('upload');
    }
}

function saveAndExit() {
    saveState();
    alert('Session saved! You can resume later.');
    showView('upload');
}

function retryQuiz() {
    state.userAnswers = {};
    state.bookmarkedQuestions.clear();
    state.timer.elapsed = 0;
    renderQuestions();
}

function newSession() {
    if (state.timer.interval) clearInterval(state.timer.interval);
    
    state.file = null;
    state.documentId = null;
    state.sessionId = null;
    state.documentInfo = null;
    state.questions = [];
    state.userAnswers = {};
    state.bookmarkedQuestions.clear();
    state.results = null;
    state.chatMessages = [];
    state.timer = { started: null, elapsed: 0, interval: null };
    
    document.getElementById('file-input').value = '';
    document.getElementById('file-name').textContent = 'No file selected';
    document.getElementById('upload-btn').disabled = true;
    document.getElementById('start-generation-btn').disabled = true;
    
    saveState();
    showView('upload');
    renderActiveSession();
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;
    
    state.chatMessages.push({ role: 'user', content: message });
    renderChatMessages();
    input.value = '';
    
    const btn = document.getElementById('chat-send-btn');
    btn.disabled = true;
    
    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id: state.documentId,
                message: message,
                history: state.chatMessages,
                wrong_questions: state.results?.wrong || [],
                language: state.language
            })
        });
        
        if (!response.ok) throw new Error('Chat failed');
        
        const data = await response.json();
        state.chatMessages.push({ role: 'assistant', content: data.response });
        renderChatMessages();
        saveState();
    } catch (error) {
        state.chatMessages.push({ role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' });
        renderChatMessages();
    } finally {
        btn.disabled = false;
    }
}

function renderChatMessages() {
    const container = document.getElementById('chat-messages');
    
    if (state.chatMessages.length === 0) {
        const initialMsg = state.results?.wrong.length > 0
            ? `I see you got ${state.results.wrong.length} question(s) incorrect. Would you like to discuss any of them?`
            : '🎉 Perfect score! Do you have any questions about the topic?';
        
        state.chatMessages.push({ role: 'assistant', content: initialMsg });
    }
    
    container.innerHTML = state.chatMessages.map(msg => {
        const escapedContent = msg.content
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');

        return `
            <div class="chat-message ${msg.role}">
                ${msg.content}
                ${msg.role === 'assistant' ? `
                    <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem;">
                        <button class="action-btn copy-btn" data-message-content="${escapedContent}">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events: none;">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                            </svg>
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
    
    container.scrollTop = container.scrollHeight;
}

function copyMessage(text) {
    const tempEl = document.createElement('textarea');
    tempEl.innerHTML = text;
    navigator.clipboard.writeText(tempEl.value);
    alert('Copied to clipboard!');
}

function exportChat() {
    const text = state.chatMessages.map(msg => 
        `${msg.role.toUpperCase()}: ${msg.content}`
    ).join('\n\n');
    
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'chat-export.txt';
    a.click();
    URL.revokeObjectURL(url);
}

async function updateAnalytics() {
    try {
        const response = await fetch(`${API_URL}/analytics`);
        if (!response.ok) throw new Error('Failed to load analytics');

        const data = await response.json();

        document.getElementById('total-sessions').textContent = data.total_sessions;
        document.getElementById('total-questions').textContent = data.total_questions;
        document.getElementById('avg-score').textContent = `${data.avg_score}%`;
    
        renderTopicChart();
    } catch (error) {
        console.error(error);
        document.getElementById('total-sessions').textContent = 'Error';
    }
}

function renderTopicChart() {
    const container = document.getElementById('topic-chart');
    container.innerHTML = '<p style="color: var(--text-secondary);">Topic data not available in this version.</p>';
}

function handleKeyboardShortcut(e) {
    if (state.currentView !== 'answering') return;
    
    if (e.key >= '1' && e.key <= '4' && !e.target.matches('input')) {
        e.preventDefault();
        const currentQuestion = document.querySelector('.question-card');
        if (currentQuestion) {
            const options = currentQuestion.querySelectorAll('input[type="radio"]');
            const index = parseInt(e.key) - 1;
            if (options[index]) {
                options[index].click();
            }
        }
    }
    
    if (e.key === 'b' || e.key === 'B') {
        e.preventDefault();
        const firstQuestion = state.questions[0];
        if (firstQuestion) {
            toggleBookmark(firstQuestion.id);
        }
    }
    
    if (e.key === ' ' && !e.target.matches('input')) {
        e.preventDefault();
        const currentQuestion = document.querySelector('.question-card');
        if (currentQuestion) {
            const nextQuestion = currentQuestion.nextElementSibling;
            if (nextQuestion) {
                nextQuestion.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }
}

function showHelp() {
    alert(`Keyboard Shortcuts:
    
• 1-4: Select answer option
• Space: Scroll to next question
• B: Toggle bookmark on current question
• Enter: Submit (when in chat)

Features:
• Auto-save every 30 seconds
• Dark/Light theme toggle
• Multi-language support
• Session history tracking
• Performance analytics
• AI-powered discussion`);
}

function renderUI() {
    renderSessionHistory();
    renderActiveSession();
    updateAnalytics();
    
    if (state.documentId && state.questions.length > 0) {
        if (state.results) {
            renderResults();
        } else if (state.sessionId) {
            renderQuestions();
        } else {
            console.warn('Orphaned questions found. Starting new session...');
            startNewSession(); 
        }
    }
}

async function loadSessionResults(sessionId) {
    try {
        const response = await fetch(`${API_URL}/session/${sessionId}`);
        if (!response.ok) throw new Error('Failed to load session details');
        
        const results = await response.json();
        state.results = results;
        state.timer.elapsed = 0; 
        state.results.timeTaken = 0; 
        
        renderResults(); 
        showView('results');
    } catch (error) {
        console.error(error);
        alert('Could not load session results.');
    }
}

async function deleteSession(sessionId) {
    try {
        const response = await fetch(`${API_URL}/session/${sessionId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete session');
        
        renderSessionHistory();
        updateAnalytics(); 
        
    } catch (error)
        {
        console.error(error);
        alert('Could not delete session.');
    }
}

setInterval(() => {
    if (state.documentId) {
        saveState();
    }
}, 30000);