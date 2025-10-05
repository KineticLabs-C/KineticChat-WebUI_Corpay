// Corpay Financial Chat - Simple HTTP POST Implementation
// Enterprise-grade financial chat following industry standards

class CorpayFinancialChat {
    constructor() {
        this.apiEndpoint = '/api/corpay-chat';
        this.sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        this.currentLang = localStorage.getItem('chatLanguage') || 'en';
        
        // UI elements
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        
        this.initializeEventListeners();
        this.updateLanguageUI();
    }
    
    initializeEventListeners() {
        // Send button
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter key
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Language toggle
        document.getElementById('langToggle').addEventListener('click', () => {
            if (confirm(translations[this.currentLang].switchConfirm)) {
                this.currentLang = this.currentLang === 'en' ? 'es' : 'en';
                localStorage.setItem('chatLanguage', this.currentLang);
                this.clearChat();
                this.updateLanguageUI();
                this.sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            }
        });
        
        // Quick action buttons
        document.querySelectorAll('.quick-btn').forEach(button => {
            button.addEventListener('click', () => {
                const query = button.getAttribute(`data-query-${this.currentLang}`);
                this.messageInput.value = query;
                this.sendMessage();
            });
        });
        
        // Input state
        this.messageInput.addEventListener('input', () => {
            this.sendButton.disabled = !this.messageInput.value.trim();
        });
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // Clear input
        this.messageInput.value = '';
        this.sendButton.disabled = true;
        
        // Add user message
        this.addMessage(message, 'user');
        
        // Show loading
        this.loadingIndicator.style.display = 'flex';
        
        try {
            // Simple HTTP POST
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId
                },
                body: JSON.stringify({
                    query: message,
                    language: this.currentLang,
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Hide loading
            this.loadingIndicator.style.display = 'none';
            
            // Display response
            const responseText = data.response || "I'm sorry, I couldn't process your request.";
            this.addMessage(responseText, 'assistant');
            
        } catch (error) {
            console.error('Chat error:', error);
            this.loadingIndicator.style.display = 'none';
            this.addMessage(
                "I'm experiencing technical difficulties. Please try again later.",
                'assistant'
            );
        }
        
        // Re-enable input
        this.messageInput.focus();
    }
    
    addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = this.formatMessage(content);
        
        messageDiv.appendChild(messageContent);
        this.chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        setTimeout(() => {
            this.chatMessages.scrollTo({
                top: this.chatMessages.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }
    
    formatMessage(content) {
        // Format message content - based on old working implementation
        let formatted = content;
        
        // Headers ### text -> <strong>text</strong> (NOT <h3>)
        formatted = formatted.replace(/^### (.*$)/gim, '<strong>$1</strong>');
        
        // Bold text **text** -> <strong>text</strong>
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Lists with bullets
        formatted = formatted.replace(/^[•\-] (.*$)/gim, '<li>$1</li>');
        
        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Convert URLs to clickable links - following old implementation pattern
        formatted = this.convertUrlsToLinks(formatted);
        
        // Wrap consecutive <li> elements in <ul>
        formatted = formatted.replace(/(<li>.*?<\/li>(?:<br><li>.*?<\/li>)*)/gs, (match) => {
            return '<ul>' + match.replace(/<br>(?=<li>)/g, '') + '</ul>';
        });
        
        // Clean up excessive line breaks
        formatted = formatted.replace(/<br><br><br>/g, '<br><br>');
        
        return formatted;
    }
    
    convertUrlsToLinks(text) {
        let result = text;
        
        // Skip if already has anchor tags
        if (result.includes('<a href=')) {
            return result;
        }
        
        // 1. Process markdown links [text](url) first
        result = result.replace(
            /\[([^\]]+)\]\(([^)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // 2. Handle URLs in source citations [Sources: ...]
        result = result.replace(
            /\[Sources: ([^\]]+)\]/gi,
            (match, sourceList) => {
                const linkedSources = sourceList.split(',').map(url => {
                    url = url.trim();
                    // Add protocol if missing
                    if (url.startsWith('www.')) {
                        url = 'https://' + url;
                    }
                    // Extract domain for display
                    let displayName = url;
                    try {
                        if (url.startsWith('http')) {
                            const urlObj = new URL(url);
                            const path = urlObj.pathname.replace(/^\//, '').replace(/-/g, ' ');
                            displayName = path || urlObj.hostname.replace('www.', '');
                            if (displayName.length > 30) {
                                displayName = displayName.substring(0, 27) + '...';
                            }
                        }
                    } catch (e) {}
                    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${displayName}</a>`;
                }).join(', ');
                return `[Sources: ${linkedSources}]`;
            }
        );
        
        // 3. Handle full corpay.com URLs
        result = result.replace(
            /\b(https?:\/\/(?:www\.)?corpay\.com(?:\/[a-zA-Z0-9\-\/]*)?)\b(?![^<]*<\/a>)/gi,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // 4. Handle corpay financial URLs
        result = result.replace(
            /\b(https?:\/\/(?:www\.)?corpayfinancial\.com(?:\/[a-zA-Z0-9\-\/]*)?)\b(?![^<]*<\/a>)/gi,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // 5. Handle Google Maps URLs
        result = result.replace(
            /\b(https?:\/\/(?:www\.)?google\.com\/maps[^\s]*)\b(?![^<]*<\/a>)/gi,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // 6. Handle standalone domains (www.corpay.com without protocol)
        result = result.replace(
            /\b((?:www\.)?corpay\.com)\b(?![\/\w])(?![^<]*<\/a>)/gi,
            '<a href="https://$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // 7. Handle phone numbers
        result = result.replace(
            /\b(1[-.\s]?(?:\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}))\b(?![^<]*<\/a>)/g,
            (match, phone) => {
                const telNumber = phone.replace(/\D/g, '');
                return `<a href="tel:${telNumber}">${phone}</a>`;
            }
        );
        
        return result;
    }
    
    clearChat() {
        const messages = this.chatMessages.querySelectorAll('.message:not(#welcomeMessage)');
        messages.forEach(msg => msg.remove());
        this.messageInput.value = '';
        this.sendButton.disabled = true;
    }
    
    updateLanguageUI() {
        const t = translations[this.currentLang];
        
        // Update text content
        document.getElementById('assistantTitle').textContent = t.title;
        document.getElementById('assistantDescription').textContent = t.description;
        document.getElementById('messageInput').placeholder = t.inputPlaceholder;
        document.getElementById('helpText').textContent = t.helpText;
        document.getElementById('quickActionHeader').textContent = t.quickTopics;
        document.getElementById('sendButton').innerHTML = `<i class="fas fa-paper-plane"></i> ${t.sendButton}`;
        
        // Update language toggle
        document.getElementById('langFlag').textContent = this.currentLang === 'en' ? '🇺🇸' : '🇪🇸';
        document.getElementById('langText').textContent = this.currentLang.toUpperCase();
        
        // Update welcome message
        const welcomeContent = `
            <p><strong>${t.welcomeTitle}</strong></p>
            <p>${t.welcomeIntro}</p>
            <ul>
                <li>${t.services.payments}</li>
                <li>${t.services.cards}</li>
                <li>${t.services.expense}</li>
                <li>${t.services.international}</li>
                <li>${t.services.analytics}</li>
                <li>${t.services.security}</li>
            </ul>
            <p>${t.welcomeFooter}</p>
        `;
        document.getElementById('welcomeContent').innerHTML = welcomeContent;
        
        // Update quick button labels
        const quickButtons = document.querySelectorAll('.quick-btn .quick-text');
        const buttonKeys = ['payments', 'cards', 'solutions', 'resources', 'allTopics'];
        quickButtons.forEach((btn, index) => {
            if (buttonKeys[index] && t.quickButtons && t.quickButtons[buttonKeys[index]]) {
                btn.textContent = t.quickButtons[buttonKeys[index]];
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.corpayChat = new CorpayFinancialChat();
    console.log('Corpay Financial Chat Interface Loaded (HTTP POST)');
});