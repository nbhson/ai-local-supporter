// ===== FREE CHAT FUNCTIONS =====
async function initChatSession() {
    state.chat.model = modelSelect.value;
    chatWelcome.style.display = 'none';
    chatChatMessages.style.display = 'flex';
    chatChatMessages.innerHTML = '';
    showTypingIndicator(chatChatMessages);

    try {
        const res = await fetch('/api/chat/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: state.chat.model,
                language: state.language
            })
        });
        const data = await res.json();
        removeTypingIndicator();

        if (!res.ok) throw new Error(data.error || 'Failed to initialize chat');

        state.chat.sessionId = data.session_id;

        chatStatus.textContent = state.language === 'vi' ? '✅ Sẵn sàng' : '✅ Ready';
        chatQuickActions.style.display = 'block';

        addChatMessage('assistant', data.greeting);
        updateChatInput();
    } catch (err) {
        removeTypingIndicator();
        showToast('❌', err.message);
    }
}

function addChatMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = `
        <div class="message-avatar"><span class="material-symbols-rounded">${role === 'assistant' ? 'smart_toy' : 'person'}</span></div>
        <div class="message-bubble">${formatMessage(content)}</div>
    `;
    chatChatMessages.appendChild(msgDiv);
    chatChatMessages.scrollTop = chatChatMessages.scrollHeight;
}

async function clearChatSession() {
    if (state.chat.sessionId) {
        try { await fetch(`/api/chat/session/${state.chat.sessionId}/clear`, { method: 'POST' }); } catch (e) { }
    }
    state.chat.sessionId = null;
    chatQuickActions.style.display = 'none';
    chatChatMessages.style.display = 'none';
    chatChatMessages.innerHTML = '';
    chatWelcome.style.display = 'flex';
    chatStatus.textContent = state.language === 'vi' ? 'Chưa bắt đầu' : 'Not started';
    updateChatInput();
    showToast('🔄', state.language === 'vi' ? 'Đã xóa lịch sử chat.' : 'Cleared chat history.');
}

// ===== CODE ANALYSIS =====
async function analyzeCode() {
    const code = codeInput.value.trim();
    if (!code) {
        showToast('⚠️', state.language === 'vi' ? 'Vui lòng dán code của bạn.' : 'Please paste your code.');
        return;
    }

    state.code.model = modelSelect.value;

    analyzeCodeBtn.disabled = true;
    analyzeCodeBtn.innerHTML = `<span class="material-symbols-rounded btn-icon-left spinning">progress_activity</span> ${state.language === 'vi' ? 'Đang phân tích...' : 'Analyzing...'}`;

    try {
        const res = await fetch('/api/chat/code/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code: code,
                language: codeLanguage.value,
                model: state.code.model,
                ui_language: state.language
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Analysis failed');

        state.code.sessionId = data.session_id;
        state.code.codename = data.language !== 'auto-detect' ? `code.${getFileExtension(data.language)}` : 'code.py';

        codeFileName.textContent = state.code.codename;
        codeStatus.textContent = state.language === 'vi' ? '✅ Đã phân tích' : '✅ Analyzed';

        // Update UI panels in the sidebar
        document.querySelector('.code-input-section').style.display = 'none';
        codeInfo.style.display = 'block';
        
        // Show code quick actions, hide free chat quick actions
        chatQuickActions.style.display = 'none';
        codeQuickActions.style.display = 'block';

        // Clear free chat welcome screen and prepare chat window
        chatWelcome.style.display = 'none';
        chatChatMessages.style.display = 'flex';
        chatChatMessages.innerHTML = '';

        // Append the greeting message to the chat
        addChatMessage('assistant', data.greeting);
        updateChatInput();

        showToast('✅', state.language === 'vi' ? 'Phân tích code thành công!' : 'Code analyzed successfully!');
    } catch (err) {
        showToast('❌', err.message);
    } finally {
        analyzeCodeBtn.disabled = false;
        const t = translations[state.language];
        analyzeCodeBtn.innerHTML = `<span class="material-symbols-rounded btn-icon-left">analytics</span> ${t.analyzeCode}`;
    }
}

// Utility to get extension from language
function getFileExtension(lang) {
    const extMap = {
        'python': 'py',
        'javascript': 'js',
        'typescript': 'ts',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c',
        'go': 'go',
        'rust': 'rs',
        'sql': 'sql',
        'html': 'html',
        'css': 'css',
        'bash': 'sh'
    };
    return extMap[lang.toLowerCase()] || 'py';
}

async function clearCodeSession() {
    if (state.code.sessionId) {
        try { await fetch(`/api/chat/code/session/${state.code.sessionId}/clear`, { method: 'POST' }); } catch (e) { }
    }
    state.code.sessionId = null;
    state.code.codename = null;
    
    // Hide code info and code quick actions
    codeInfo.style.display = 'none';
    codeQuickActions.style.display = 'none';
    
    // Show code input section again
    document.querySelector('.code-input-section').style.display = 'block';
    codeInput.value = '';
    
    // Reset Chat to Free Chat mode
    chatChatMessages.style.display = 'none';
    chatChatMessages.innerHTML = '';
    chatWelcome.style.display = 'flex';
    
    // Initialize a new free chat session automatically
    await initChatSession();
    
    showToast('🔄', state.language === 'vi' ? 'Đã xóa. Trở về Free Chat.' : 'Cleared. Returned to Free Chat.');
}
