import { getAI, getGenerativeModel, GoogleAIBackend } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-ai.js";
import { firebaseConfig } from './firebase-config.js';
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js";

class VoiceRecorder {
    constructor() {
        this.recognition = null;
        this.isRecording = false;
        this.silenceTimer = null;
        this.restartTimer = null;

        // Speech recognition variables
        this.finalTranscript = '';
        this.interimTranscript = '';
        this.speechRecognitionActive = false;
        this.lastSpeechTime = null;
        
        // Conversation history
        this.conversationHistory = [];

        // Initialize Firebase AI
        console.log('Initializing Firebase app...');
        this.firebaseApp = initializeApp(firebaseConfig);
        console.log('Firebase app initialized, setting up AI service...');
        this.ai = getAI(this.firebaseApp, { backend: new GoogleAIBackend() });
        console.log('AI service initialized, creating model...');
        this.model = getGenerativeModel(this.ai, { model: "gemini-2.5-flash" });
        console.log('Gemini model ready:', this.model);

        this.initializeElements();
        this.checkBrowserSupport();
        
        // Wait for DOM to be ready before starting
        if (document.readyState === 'complete') {
            this.startRecording();
        } else {
            window.addEventListener('load', () => this.startRecording());
        }
    }

    checkBrowserSupport() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            this.showError('Speech recognition not supported in this browser. Please use Chrome, Edge, or Safari.');
            return false;
        }
        return true;
    }

    initializeElements() {
        this.status = document.getElementById('status');
        // Hardcoded values
        this.error = document.getElementById('error');
        this.transcription = document.getElementById('transcription');
        this.transcriptionText = document.getElementById('transcriptionText');
        
        // Create interim text overlay
        this.interimOverlay = document.createElement('div');
        this.interimOverlay.id = 'interim-overlay';
        document.body.appendChild(this.interimOverlay);
    }

    async startRecording() {
        try {
            this.clearError();
            if (this.transcription && this.transcriptionText) {
                this.hideTranscription();
            }

            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            // Store stream for cleanup
            this.mediaStream = stream;

            // Setup speech recognition
            this.setupSpeechRecognition();

            this.isRecording = true;

            // Reset variables (keep transcript history)
            this.interimTranscript = '';
            this.lastSpeechTime = Date.now();

            // Start speech recognition
            this.startSpeechRecognition();
            
            // Remove any existing silence timer
            if (this.silenceTimer) {
                clearTimeout(this.silenceTimer);
                this.silenceTimer = null;
            }

        } catch (error) {
            this.showError('Error accessing microphone: ' + error.message);
        }
    }

    setupSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();

        // Configure recognition
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.maxAlternatives = 1;

        // Set language (hardcoded to auto-detect)
        this.recognition.lang = 'en-US'; // Fallback if auto-detect fails

        // Event handlers
        this.recognition.onstart = () => {
            this.speechRecognitionActive = true;
            console.log('Speech recognition started');
        };

        // Use our modified onresult handler
        this.recognition.onresult = this.onresult.bind(this);

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            
            // Handle specific errors
            switch (event.error) {
                case 'network':
                    this.showError('Network error during speech recognition');
                    break;
                case 'not-allowed':
                    this.showError('Microphone access denied');
                    break;
                case 'no-speech':
                    // This is normal, just restart recognition
                    this.restartRecognitionAfterDelay();
                    break;
                default:
                    this.showError('Speech recognition error: ' + event.error);
            }
        };

        this.recognition.onend = () => {
            this.speechRecognitionActive = false;
            console.log('Speech recognition ended');
            
            // Restart recognition if we're still recording
            if (this.isRecording) {
                this.restartRecognitionAfterDelay();
            }
        };
    }

    startSpeechRecognition() {
        if (this.recognition && !this.speechRecognitionActive) {
            try {
                this.recognition.start();
            } catch (error) {
                console.error('Error starting speech recognition:', error);
                this.restartRecognitionAfterDelay();
            }
        }
    }

    restartRecognitionAfterDelay() {
        if (this.restartTimer) {
            clearTimeout(this.restartTimer);
        }

        this.restartTimer = setTimeout(() => {
            if (this.isRecording && !this.speechRecognitionActive) {
                this.startSpeechRecognition();
            }
        }, 100);
    }

    // Modified to keep recognition running continuously
    stopRecording() {
        // Just hide overlay and process any final results
        this.interimOverlay.style.display = 'none';
        this.processTranscription();
    }

    async processTranscription() {
        const finalText = this.finalTranscript.trim();
        
        if (finalText) {
            this.showTranscription(finalText, true);
            
            try {
                // Send transcription to Gemini
                const result = await this.model.generateContent(finalText);
                const response = result.response;
                const geminiText = response.text();
                
                // Show Gemini response
                this.showTranscription(geminiText, true);
            } catch (error) {
                console.error('Gemini API error:', error);
                this.showError('Gemini processing failed: ' + error.message);
            }
        } else {
            this.showTranscription('(No speech detected)', true);
        }
    }

    // Simplified transcription handler with direct interim display
    onresult = async (event) => {
        // Clear overlay initially
        this.interimOverlay.style.display = 'none';

        // Process all results
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                // Hide overlay for final text
                this.interimOverlay.style.display = 'none';
                
                // Add user message to history
                this.conversationHistory.push({
                    speaker: 'user',
                    text: transcript,
                    timestamp: new Date()
                });

                // Immediately show user message
                this.updateDisplay(transcript, null);

                // Process with Gemini using full conversation context
                try {
                    let conversationContext = this.conversationHistory.map(msg => 
                        `${msg.speaker === 'user' ? 'User' : 'Assistant'}: ${msg.text}`
                    ).join('\n\n');
                    
                    const result = await this.model.generateContent({
                        contents: [{
                            role: 'user',
                            parts: [{text: `${conversationContext}\n\nUser: ${transcript}`}]
                        }]
                    });
                    const response = result.response;
                    const geminiText = response.text();
                    
                    // Add Gemini response to history
                    this.conversationHistory.push({
                        speaker: 'gemini',
                        text: geminiText,
                        timestamp: new Date()
                    });

                    // Update with Gemini response
                    this.updateDisplay(null, geminiText);
                } catch (error) {
                    console.error('Gemini API error:', error);
                    this.showError('Gemini processing failed: ' + error.message);
                }
            } else {
                // Directly show interim text in overlay
                this.interimOverlay.textContent = transcript;
                this.interimOverlay.style.display = 'block';
            }
        }
    };

    // Helper to update display from conversation history
    updateDisplay(finalText, geminiText, isInterim = false) {
        let formattedText = '';
        
        // Add all conversation history in reverse order (newest first)
        for (let i = this.conversationHistory.length - 1; i >= 0; i--) {
            const msg = this.conversationHistory[i];
            const divClass = msg.speaker === 'user' ? 'user-speech' : 'gemini-response';
            formattedText += `<div class="${divClass}">${msg.text}</div>`;
        }

        // Add current interim text if present
        if (isInterim) {
            formattedText += `<div class="interim-speech">${geminiText}</div>`;
        }

        this.transcriptionText.innerHTML = formattedText;
        this.transcriptionText.scrollTop = 0;
        this.transcription.classList.remove('empty');
    }

    showTranscription(text) {
        this.transcriptionText.innerHTML = text;
        this.transcription.classList.remove('empty');
    }

    hideTranscription() {
        this.transcription.classList.add('empty');
        this.transcriptionText.textContent = 'Your speech will appear here...';
        this.transcriptionText.style.opacity = '1';
        this.transcriptionText.style.fontStyle = 'normal';
    }

    showError(message) {
        try {
            if (this.error && this.error.textContent !== undefined) {
                this.error.textContent = message;
                setTimeout(() => {
                    if (this.error) this.error.textContent = '';
                }, 5000);
            }
            console.error(message);
        } catch (e) {
            console.error('Error showing error message:', e);
        }
    }

    clearError() {
        if (this.error) {
            this.error.textContent = '';
        }
    }
}

// Initialize the app when page loads
document.addEventListener('DOMContentLoaded', () => {
    new VoiceRecorder();
});
