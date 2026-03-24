/**
 * interview.js — Interview flow controller
 * Handles: Web Speech API (STT/TTS), interview loop, AJAX calls, UI updates
 */

(function () {
    'use strict';

    // ─── Configuration from Django template ─────────────────────────
    const CONFIG = window.INTERVIEW_DATA;
    const questions = CONFIG.questions;
    const totalQ = CONFIG.totalQuestions;
    let currentQ = 0;          // 0-indexed current question
    let answers = [];          // Collected answers
    let isListening = false;
    let recognition = null;
    let currentTranscript = '';

    // ─── DOM Elements ───────────────────────────────────────────────
    const chatMessages = document.getElementById('chat-messages');
    const micBtn = document.getElementById('mic-btn');
    const micLabel = document.getElementById('mic-label');
    const skipBtn = document.getElementById('skip-btn');
    const aiThinking = document.getElementById('ai-thinking');
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const currentQEl = document.getElementById('current-q');
    const liveTranscript = document.getElementById('live-transcript');
    const transcriptText = document.getElementById('transcript-text');

    // ─── Speech Synthesis (Text-to-Speech) ──────────────────────────

    /**
     * Speak text using the browser's SpeechSynthesis API.
     * Tries to select a female English voice.
     */
    function speak(text) {
        return new Promise((resolve) => {
            if (!('speechSynthesis' in window)) {
                console.warn('SpeechSynthesis not supported');
                resolve();
                return;
            }

            // Cancel any ongoing speech
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.95;
            utterance.pitch = 1.1;
            utterance.volume = 1.0;

            // Try to pick a female voice
            const voices = window.speechSynthesis.getVoices();
            const femaleVoice = voices.find(v =>
                v.lang.startsWith('en') &&
                (v.name.toLowerCase().includes('female') ||
                 v.name.toLowerCase().includes('samantha') ||
                 v.name.toLowerCase().includes('victoria') ||
                 v.name.toLowerCase().includes('karen') ||
                 v.name.toLowerCase().includes('moira') ||
                 v.name.toLowerCase().includes('fiona') ||
                 v.name.toLowerCase().includes('zira') ||
                 v.name.toLowerCase().includes('susan'))
            ) || voices.find(v => v.lang.startsWith('en'));

            if (femaleVoice) {
                utterance.voice = femaleVoice;
            }

            utterance.onend = resolve;
            utterance.onerror = () => resolve();

            window.speechSynthesis.speak(utterance);
        });
    }

    // Pre-load voices (some browsers load them async)
    if ('speechSynthesis' in window) {
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = () => {
            window.speechSynthesis.getVoices();
        };
    }

    // ─── Speech Recognition (Speech-to-Text) ───────────────────────

    /**
     * Initialize the Web Speech API for speech recognition.
     */
    function initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            addMessage('system', '⚠️ Your browser does not support speech recognition. Please use Chrome for the best experience. You can type your answers using the skip button.');
            micBtn.disabled = true;
            micBtn.style.opacity = '0.5';
            return;
        }

        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isListening = true;
            micBtn.classList.add('listening');
            micLabel.textContent = 'Listening...';
            liveTranscript.style.display = 'block';
            transcriptText.textContent = '';
            currentTranscript = '';
        };

        recognition.onresult = (event) => {
            let interim = '';
            let final = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                if (event.results[i].isFinal) {
                    final += event.results[i][0].transcript;
                } else {
                    interim += event.results[i][0].transcript;
                }
            }
            if (final) {
                currentTranscript += final;
            }
            transcriptText.textContent = currentTranscript + interim;
        };

        recognition.onend = () => {
            isListening = false;
            micBtn.classList.remove('listening');
            micLabel.textContent = 'Tap to Speak';
            liveTranscript.style.display = 'none';

            // If we have a transcript, submit the answer
            if (currentTranscript.trim()) {
                submitAnswer(currentTranscript.trim());
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            isListening = false;
            micBtn.classList.remove('listening');
            micLabel.textContent = 'Tap to Speak';
            liveTranscript.style.display = 'none';

            if (event.error === 'not-allowed') {
                addMessage('system', '⚠️ Microphone access denied. Please allow microphone access in your browser settings.');
            }
        };
    }

    // ─── UI Helpers ─────────────────────────────────────────────────

    /**
     * Add a message bubble to the chat area.
     * @param {'ai'|'user'|'system'} type - Message sender
     * @param {string} text - Message content
     */
    function addMessage(type, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${type}-message`;

        if (type === 'ai') {
            msgDiv.innerHTML = `
                <div class="message-avatar">👩‍💼</div>
                <div class="message-bubble">
                    <span class="message-sender">Sarah (AI Interviewer)</span>
                    <p class="message-text">${escapeHtml(text)}</p>
                </div>`;
        } else if (type === 'user') {
            msgDiv.innerHTML = `
                <div class="message-bubble user-bubble">
                    <span class="message-sender">You</span>
                    <p class="message-text">${escapeHtml(text)}</p>
                </div>
                <div class="message-avatar">🧑</div>`;
        } else {
            msgDiv.innerHTML = `<div class="system-notice">${text}</div>`;
        }

        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function updateProgress() {
        const pct = Math.round(((currentQ) / totalQ) * 100);
        progressFill.style.width = pct + '%';
        progressPercent.textContent = pct + '%';
        currentQEl.textContent = Math.min(currentQ + 1, totalQ);
    }

    function showThinking(show) {
        aiThinking.style.display = show ? 'flex' : 'none';
        if (show) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function setControlsEnabled(enabled) {
        micBtn.disabled = !enabled;
        skipBtn.disabled = !enabled;
        micBtn.style.opacity = enabled ? '1' : '0.5';
        skipBtn.style.opacity = enabled ? '1' : '0.5';
    }

    // ─── Interview Flow ─────────────────────────────────────────────

    /**
     * Start the interview with a greeting, then ask the first question.
     */
    async function startInterview() {
        setControlsEnabled(false);

        // AI greeting
        const greeting = "Hello! I'm Sarah, and I'll be conducting your interview today. Thank you for applying — let's get started! I'll ask you a series of questions, and please take your time answering each one.";
        addMessage('ai', greeting);
        await speak(greeting);

        // Small pause
        await delay(500);

        // Ask first question
        askQuestion();
    }

    /**
     * Display and speak the current question.
     */
    async function askQuestion() {
        if (currentQ >= totalQ) {
            finishInterview();
            return;
        }

        updateProgress();
        setControlsEnabled(false);
        showThinking(true);
        await delay(800);
        showThinking(false);

        const question = questions[currentQ];
        addMessage('ai', question);
        await speak(question);

        // Enable controls for user to respond
        setControlsEnabled(true);
    }

    /**
     * Submit the user's answer and get AI response.
     */
    async function submitAnswer(answerText) {
        if (!answerText) return;

        // Show user's answer
        addMessage('user', answerText);
        answers.push(answerText);
        setControlsEnabled(false);

        // Send to backend for AI acknowledgment
        showThinking(true);

        try {
            const response = await fetch(CONFIG.askUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    interview_id: CONFIG.interviewId,
                    question: questions[currentQ],
                    answer: answerText,
                    question_number: currentQ + 1,
                    total_questions: totalQ,
                }),
            });

            const data = await response.json();
            showThinking(false);

            if (data.error) {
                addMessage('system', '⚠️ ' + data.error);
            } else if (data.response) {
                addMessage('ai', data.response);
                await speak(data.response);
            }
        } catch (err) {
            showThinking(false);
            addMessage('system', '⚠️ Network error. Moving to next question.');
            console.error('API error:', err);
        }

        // Move to next question
        currentQ++;
        await delay(500);
        askQuestion();
    }

    /**
     * Finish the interview and navigate to evaluation.
     */
    async function finishInterview() {
        updateProgress();
        setControlsEnabled(false);

        const closingMsg = "Thank you so much for completing all the questions! Let me evaluate your responses. This will take a moment...";
        addMessage('ai', closingMsg);
        await speak(closingMsg);

        showThinking(true);

        try {
            const response = await fetch(CONFIG.evaluateUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    interview_id: CONFIG.interviewId,
                    questions: questions,
                    answers: answers,
                }),
            });

            const data = await response.json();
            showThinking(false);

            if (data.error) {
                addMessage('system', '⚠️ Evaluation error: ' + data.error);
                return;
            }

            addMessage('ai', "Your evaluation is ready! Redirecting to your results...");
            await speak("Your evaluation is ready! Let me show you your results.");
            await delay(1500);

            // Redirect to results page
            window.location.href = CONFIG.resultUrl;

        } catch (err) {
            showThinking(false);
            addMessage('system', '⚠️ Failed to evaluate. Please try again.');
            console.error('Evaluation error:', err);
        }
    }

    // ─── Event Listeners ────────────────────────────────────────────

    // Mic button: toggle recording
    micBtn.addEventListener('click', () => {
        if (!recognition) {
            // Fallback: prompt for typed input
            const answer = prompt('Type your answer:');
            if (answer && answer.trim()) {
                submitAnswer(answer.trim());
            }
            return;
        }

        if (isListening) {
            recognition.stop();
        } else {
            try {
                recognition.start();
            } catch (e) {
                console.error('Recognition start error:', e);
            }
        }
    });

    // Skip button: skip current question or type answer
    skipBtn.addEventListener('click', () => {
        if (isListening && recognition) {
            recognition.stop();
        }

        // Allow typing as fallback
        const answer = prompt('Type your answer (or leave empty to skip):');
        if (answer && answer.trim()) {
            submitAnswer(answer.trim());
        } else {
            submitAnswer('(No answer provided)');
        }
    });

    // ─── Utility ────────────────────────────────────────────────────

    function delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ─── Initialize ─────────────────────────────────────────────────

    initRecognition();
    startInterview();

})();
