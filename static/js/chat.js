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

