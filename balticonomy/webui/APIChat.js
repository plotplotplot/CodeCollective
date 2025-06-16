document.addEventListener('DOMContentLoaded', function () {
    const apiUrlInput = document.getElementById('apiUrlInput');
    const dropdownButton = document.getElementById('dropdownButton');
    const dropdownMenu = document.getElementById('dropdownMenu');
    const responsesContainer = document.getElementById('responsesContainer');
    const promptInput = document.getElementById('promptInput');
    const sendButton = document.getElementById('sendButton');
    const errorMessage = document.getElementById('errorMessage');
    const defaultApiUrl = 'https://ollama.app.codecollective.us/api/generate';
    let apiUrl = localStorage.getItem('lastUsedUrl') || defaultApiUrl;
    let urlHistory = JSON.parse(localStorage.getItem('urlHistory')) || [];
    let conversationHistory = JSON.parse(localStorage.getItem('conversationHistory')) || [];
    
    // If urlHistory is empty, add the default Ollama URL
    if (urlHistory.length === 0) {
        saveUrl(defaultApiUrl)
    }
    apiUrlInput.value = apiUrl;
    updateDropdown();
    loadConversation();
    
    function updateDropdown() {
        dropdownMenu.innerHTML = urlHistory.length
            ? urlHistory.map(url => `<div class="dropdown-item">
                    <span class="select-url">${url}</span>
                    <button class="delete-button">🗑️</button>
                </div>`).join('')
            : '<div class="dropdown-item">No history</div>';
    }
    
    function loadConversation() {
        conversationHistory.forEach(message => {
            addMessageToUI(message.sender, message.body, message.avatarUrl, message.timestamp);
        });
    }
    
    function saveConversation() {
        localStorage.setItem('conversationHistory', JSON.stringify(conversationHistory));
    }
    
    function clearConversation() {
        conversationHistory = [];
        responsesContainer.innerHTML = '';
        saveConversation();
        addMessage('System', 'Conversation cleared', './system.png');
    }
    
    function addMessage(sender, body, avatarUrl) {
        const timestamp = new Date().toISOString();
        const message = { sender, body: typeof body === 'string' ? body : '[Non-text content]', avatarUrl, timestamp };
        
        // Don't save system messages about URL changes to conversation history
        if (!(sender === 'System' && typeof body === 'string' && body.includes('API URL set to'))) {
            conversationHistory.push(message);
            saveConversation();
        }
        
        addMessageToUI(sender, body, avatarUrl, timestamp);
    }
    
    function addMessageToUI(sender, body, avatarUrl, timestamp) {
        const messageDiv = createMessageElement(sender, body, avatarUrl, timestamp);
        responsesContainer.appendChild(messageDiv);
        responsesContainer.scrollTop = responsesContainer.scrollHeight;
    }
    
    function createMessageElement(sender, body, avatarUrl, timestamp) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message');
    
        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('message-avatar');
        avatarDiv.innerHTML = avatarUrl ? `<img src="${avatarUrl}" alt="Avatar">` : `<div class="default-avatar">${sender[0]}</div>`;
    
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
    
        // Generate timestamp display
        const timestampDisplay = new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
        messageContent.innerHTML = `
            <div class="message-header">
                <span class="message-sender">${sender}</span>
                <span class="message-timestamp">${timestampDisplay}</span>
            </div>
            <div class="message-body"></div>
        `;
    
        const messageBody = messageContent.querySelector('.message-body');
        if (typeof body === 'string') {
            messageBody.textContent = body;
        } else {
            messageBody.appendChild(body);
        }
    
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(messageContent);
        return messageDiv;
    }
    
    dropdownButton.addEventListener('click', () => {
        dropdownMenu.style.display = dropdownMenu.style.display === 'none' ? 'block' : 'none';
    });
    
    dropdownMenu.addEventListener('click', (e) => {
        if (e.target.classList.contains('select-url')) {
            apiUrl = e.target.textContent;
            apiUrlInput.value = apiUrl;
            saveUrl(apiUrl);
            dropdownMenu.style.display = 'none';
        } else if (e.target.classList.contains('delete-button')) {
            const parent = e.target.closest('.dropdown-item');
            const urlToDelete = parent.querySelector('.select-url').textContent;
            urlHistory = urlHistory.filter(url => url !== urlToDelete);
            localStorage.setItem('urlHistory', JSON.stringify(urlHistory));
            updateDropdown();
        }
    });
    
    apiUrlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            apiUrl = apiUrlInput.value.trim();
            saveUrl(apiUrl);
        }
    });
    
    function saveUrl(url) {
        if (!url.trim()) return;
        // Set the last used URL
        localStorage.setItem('lastUsedUrl', url);
        // Add to history if it doesn't exist
        if (!urlHistory.includes(url)) {
            urlHistory.push(url);
            localStorage.setItem('urlHistory', JSON.stringify(urlHistory));
            updateDropdown();
        }
        addMessage('System', `API URL set to: ${url}`, './system.png');
    }
    
    function buildConversationContext() {
        // Build context from conversation history, excluding system messages
        const contextMessages = conversationHistory.filter(msg => msg.sender !== 'System');
        
        if (contextMessages.length === 0) return '';
        
        // Create a conversation context string
        let context = "Previous conversation:\n";
        contextMessages.forEach(msg => {
            if (msg.sender === 'You') {
                context += `Human: ${msg.body}\n`;
            } else if (msg.sender === 'Llama') {
                context += `Assistant: ${msg.body}\n`;
            }
        });
        
        return context + "\nCurrent message:\n";
    }
    
    async function generateResponse() {
        const prompt = promptInput.value.trim();
        if (!prompt) return;
        
        addMessage('You', prompt, './user.png');
        promptInput.value = '';
        sendButton.disabled = true;
        sendButton.textContent = 'Generating...';
        errorMessage.style.display = 'none';
        
        try {
            const conversationContext = buildConversationContext();
            const fullPrompt = conversationContext + prompt;
            
            console.log('Sending request to:', apiUrl);
            console.log('Request body:', { model: "llama3.2", prompt: fullPrompt, stream: true });
            
            const requestBody = {
                model: "llama3.2", // Default model, can be changed to other available models
                prompt: fullPrompt,
                stream: true
            };
            
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });
            
            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to generate response. Status: ${response.status}, Response: ${errorText}`);
            }
            
            // Create placeholder message for streaming response
            const timestamp = new Date().toISOString();
            const messageDiv = createMessageElement('Llama', '', './child.jpg', timestamp);
            const messageBody = messageDiv.querySelector('.message-body');
            responsesContainer.appendChild(messageDiv);
            responsesContainer.scrollTop = responsesContainer.scrollHeight;
            
            let fullResponse = '';
            
            // Handle streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            try {
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    
                    // Decode the chunk and add to buffer
                    buffer += decoder.decode(value, { stream: true });
                    
                    // Split by newlines to get individual JSON objects
                    const lines = buffer.split('\n');
                    
                    // Keep the last incomplete line in buffer
                    buffer = lines.pop() || '';
                    
                    // Process each complete line
                    for (const line of lines) {
                        if (line.trim() === '') continue;
                        
                        try {
                            const data = JSON.parse(line);
                            
                            if (data.response) {
                                fullResponse += data.response;
                                messageBody.textContent = fullResponse;
                                responsesContainer.scrollTop = responsesContainer.scrollHeight;
                            }
                            
                            if (data.done === true) {
                                // Save complete message to conversation history
                                const message = { 
                                    sender: 'Llama', 
                                    body: fullResponse, 
                                    avatarUrl: './child.jpg', 
                                    timestamp: timestamp 
                                };
                                conversationHistory.push(message);
                                saveConversation();
                                return; // Exit the function
                            }
                        } catch (parseError) {
                            console.warn('Failed to parse JSON line:', line, parseError);
                            continue;
                        }
                    }
                }
                
                // Process any remaining buffer content
                if (buffer.trim()) {
                    try {
                        const data = JSON.parse(buffer);
                        if (data.response) {
                            fullResponse += data.response;
                            messageBody.textContent = fullResponse;
                        }
                    } catch (parseError) {
                        console.warn('Failed to parse final buffer:', buffer, parseError);
                    }
                }
                
                // Save final message if not already saved
                if (fullResponse && !conversationHistory.some(msg => msg.timestamp === timestamp)) {
                    const message = { 
                        sender: 'Llama', 
                        body: fullResponse, 
                        avatarUrl: './child.jpg', 
                        timestamp: timestamp 
                    };
                    conversationHistory.push(message);
                    saveConversation();
                }
                
            } catch (streamError) {
                console.error('Streaming error:', streamError);
                throw new Error(`Streaming failed: ${streamError.message}`);
            }
            
        } catch (err) {
            addMessage('System', `Error generating response: ${err.message}`, './system.png');
            errorMessage.textContent = `Error generating response: ${err.message}`;
            errorMessage.style.display = 'block';
        } finally {
            sendButton.disabled = false;
            sendButton.textContent = 'Send';
        }
    }
    
    sendButton.addEventListener('click', generateResponse);
    
    // Add clear conversation button functionality if it exists
    const clearButton = document.getElementById('clearButton');
    if (clearButton) {
        clearButton.addEventListener('click', clearConversation);
    }
    
    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            generateResponse();
        }
    });
});