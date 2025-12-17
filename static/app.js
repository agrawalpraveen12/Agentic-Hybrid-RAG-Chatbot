document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const memoryContent = document.getElementById('memory-content');
    const clearHistoryBtn = document.getElementById('clear-history-btn');

    let threadId = localStorage.getItem('nova_thread_id');
    if (!threadId) {
        threadId = crypto.randomUUID();
        localStorage.setItem('nova_thread_id', threadId);
    }

    // --- History Loading ---
    async function loadHistory() {
        try {
            const res = await fetch(`/api/history?thread_id=${threadId}`);
            const data = await res.json();
            data.forEach(msg => {
                appendMessage(msg.role, msg.content, false);
            });
            scrollToBottom();
        } catch (e) {
            console.error("Failed to load history", e);
        }
    }

    // --- Memory Loading ---
    async function loadMemory() {
        try {
            const res = await fetch('/api/memory');
            const data = await res.json();
            const factsHtml = data.facts.map(f => `<div>• ${f[0]}: ${f[1]}</div>`).join('') || 'No facts yet.';
            memoryContent.innerHTML = `
                <div style="margin-bottom:0.5rem"><strong>Name:</strong> ${data.name || 'Unknown'}</div>
                <div><strong>Facts:</strong></div>
                <div style="padding-left:0.5rem">${factsHtml}</div>
            `;
        } catch (e) {
            console.error("Failed to load memory", e);
        }
    }

    // --- Chat Logic ---
    function appendMessage(role, text, animate = true) {
        const div = document.createElement('div');
        div.className = `message ${role}`;
        
        let contentHtml = text;
        // Simple markdown parsing (could use a library like marked.js)
        if (role === 'assistant') {
            // Very basic bold/code parsing for demo
            contentHtml = text
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n/g, '<br>');
        }

        div.innerHTML = `
            <div class="avatar"><i class="fas ${role === 'user' ? 'fa-user' : 'fa-robot'}"></i></div>
            <div class="content">${contentHtml}</div>
        `;
        chatContainer.appendChild(div);
        scrollToBottom();
        return div;
    }

    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // User Message
        appendMessage('user', text);
        userInput.value = '';
        userInput.style.height = 'auto'; // Reset height

        // Assistant Placeholder
        const botDiv = document.createElement('div');
        botDiv.className = 'message assistant';
        botDiv.innerHTML = `
            <div class="avatar"><i class="fas fa-robot"></i></div>
            <div class="content"><span class="typing-cursor">▌</span></div>
        `;
        chatContainer.appendChild(botDiv);
        scrollToBottom();

        const contentDiv = botDiv.querySelector('.content');
        let accumulatedResponse = "";

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, thread_id: threadId })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                accumulatedResponse += chunk;
                
                // Simple realtime rendering
                contentDiv.innerHTML = accumulatedResponse
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br>') + '<span class="typing-cursor">▌</span>';
                
                scrollToBottom();
            }
            // Remove cursor
            contentDiv.innerHTML = contentDiv.innerHTML.replace('<span class="typing-cursor">▌</span>', '');
            
            // Refresh memory panel after chat (in case facts were added)
            loadMemory();

        } catch (e) {
            contentDiv.innerHTML = `<span style="color:red">Error: ${e.message}</span>`;
        }
    }

    // --- Event Listeners ---
    sendBtn.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // File Upload Main Logic
    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const statusDiv = document.getElementById('upload-status');
        statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading & Indexing...';
        
        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                statusDiv.innerHTML = `<i class="fas fa-check" style="color:#10a37f"></i> ${data.message}`;
            } else {
                throw new Error(data.detail || 'Upload failed');
            }
        } catch (e) {
            statusDiv.innerHTML = `<i class="fas fa-times" style="color:red"></i> ${e.message}`;
        }
    }

    // Drag and Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#7447f6';
        dropZone.style.backgroundColor = 'rgba(116, 71, 246, 0.1)';
    });

    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#444';
        dropZone.style.backgroundColor = 'transparent';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#444';
        dropZone.style.backgroundColor = 'transparent';
        
        if (e.dataTransfer.files.length) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length) {
            uploadFile(fileInput.files[0]);
        }
    });

    clearHistoryBtn.addEventListener('click', async () => {
        if (confirm('Clear chat history?')) {
            await fetch(`/api/history?thread_id=${threadId}`, { method: 'DELETE' });
            chatContainer.innerHTML = '';
            // Restore welcome message
            const div = document.createElement('div');
            div.className = 'message assistant';
            div.innerHTML = `
                <div class="avatar"><i class="fas fa-robot"></i></div>
                <div class="content">History cleared. Ready for a new topic!</div>
            `;
            chatContainer.appendChild(div);
        }
    });

    // --- Init ---
    loadHistory();
    loadMemory();
});
