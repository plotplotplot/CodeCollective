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

        this.initializeElements();
        this.setupEventListeners();
        this.checkBrowserSupport();
    }

    checkBrowserSupport() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            this.showError('Speech recognition not supported in this browser. Please use Chrome, Edge, or Safari.');
            this.micButton.disabled = true;
            return false;
        }
        return true;
    }

    initializeElements() {
        this.micButton = document.getElementById('micButton');
        this.status = document.getElementById('status');
        // Hardcoded values
        this.silenceDuration = { value: 2000 };
        this.language = { value: '' }; // Auto-detect
        this.task = { value: 'transcribe' };
        this.endpoint = { value: 'https://whisper.app.codecollective.us/asr' };
        this.error = document.getElementById('error');
        this.transcription = document.getElementById('transcription');
        this.transcriptionText = document.getElementById('transcriptionText');
    }

    setupEventListeners() {
        this.micButton.addEventListener('click', () => {
            if (!this.isRecording) {
                this.startRecording();
            } else {
                this.stopRecording();
            }
        });
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
            this.updateUI('recording');

            // Reset variables
            this.finalTranscript = '';
            this.interimTranscript = '';
            this.lastSpeechTime = Date.now();

            // Start speech recognition
            this.startSpeechRecognition();

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

        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = this.finalTranscript;

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                    // Add red circle marker when speech segment ends
                    finalTranscript += '\n\u25CF\n'; // Unicode red circle
                } else {
                    interimTranscript += transcript;
                }
            }

            this.finalTranscript = finalTranscript;
            this.interimTranscript = interimTranscript;

            // Update display with both final and interim results
            const displayText = (finalTranscript + interimTranscript).trim();
            if (displayText) {
                this.showTranscription(displayText, !interimTranscript);
            }
        };

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

    stopRecording() {
        if (this.isRecording) {
            this.isRecording = false;
            this.updateUI('processing');

            // Stop speech recognition
            if (this.recognition && this.speechRecognitionActive) {
                this.recognition.stop();
            }

            // Clear restart timer
            if (this.restartTimer) {
                clearTimeout(this.restartTimer);
                this.restartTimer = null;
            }

            // Clear silence timer
            if (this.silenceTimer) {
                clearTimeout(this.silenceTimer);
                this.silenceTimer = null;
            }

            // Stop microphone stream
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => track.stop());
                this.mediaStream = null;
            }

            // Process final results
            this.processTranscription();
        }
    }

    async processTranscription() {
        const finalText = this.finalTranscript.trim();
        
        if (finalText) {
            this.showTranscription(finalText, true);
            this.status.textContent = 'Processing order...';
            
            try {
                this.status.textContent = 'Transcription processed locally';
            } catch (error) {
                this.status.textContent = 'Error processing transcription';
                console.error('Processing error:', error);
            }
        } else {
            this.showTranscription('(No speech detected)', true);
            this.status.textContent = 'No speech detected';
        }

        setTimeout(() => this.updateUI('idle'), 2000);
    }

    // Modified onresult handler to handle silence timeout
    onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = this.finalTranscript;

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
                // Add red circle marker when speech segment ends
                finalTranscript += '\n\u25CF\n'; // Unicode red circle
            } else {
                interimTranscript += transcript;
            }
        }

        this.finalTranscript = finalTranscript;
        this.interimTranscript = interimTranscript;

        // Update last speech time
        this.lastSpeechTime = Date.now();

        // Clear any existing silence timer
        if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
        }

        // Set new silence timer if we have speech
        if (finalTranscript || interimTranscript) {
            this.silenceTimer = setTimeout(() => {
                if (this.isRecording) {
                    this.stopRecording();
                }
            }, parseInt(this.silenceDuration.value));
        }

        // Update display with both final and interim results
        const displayText = (finalTranscript + interimTranscript).trim();
        if (displayText) {
            this.showTranscription(displayText, !interimTranscript);
        }
    };

    showTranscription(text, isFinal = false) {
        this.transcriptionText.innerHTML = text;
        this.transcription.classList.remove('empty');
        
        // Add visual indication for interim vs final results
        if (isFinal) {
            this.transcriptionText.style.opacity = '1';
            this.transcriptionText.style.fontStyle = 'normal';
        } else {
            this.transcriptionText.style.opacity = '0.7';
            this.transcriptionText.style.fontStyle = 'italic';
        }
    }

    hideTranscription() {
        this.transcription.classList.add('empty');
        this.transcriptionText.textContent = 'Your speech will appear here...';
        this.transcriptionText.style.opacity = '1';
        this.transcriptionText.style.fontStyle = 'normal';
    }

    updateUI(state) {
        this.micButton.className = 'mic-button';

        switch (state) {
            case 'recording':
                this.micButton.classList.add('recording');
                this.micButton.textContent = '⏹️';
                this.status.textContent = 'Listening for speech...';
                break;
            case 'processing':
                this.micButton.classList.add('processing');
                this.micButton.textContent = '⏳';
                this.status.textContent = 'Finalizing transcription...';
                break;
            case 'idle':
            default:
                this.micButton.textContent = '🎤';
                this.status.textContent = 'Click the microphone to start';
                break;
        }
    }

    showError(message) {
        if (this.error) {
            this.error.textContent = message;
            setTimeout(() => {
                if (this.error) this.error.textContent = '';
            }, 5000);
        }
        console.error(message);
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
