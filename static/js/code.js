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
        const res = await fetch('/api/code/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code: code,
                language: codeLanguage.value,
                model: state.code.model,
                lang_preference: state.language
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Analysis failed');

        state.code.sessionId = data.session_id;
        state.code.codename = data.filename || 'code.py';

        codeFileName.textContent = state.code.codename;
        codeStatus.textContent = state.language === 'vi' ? '✅ Đã phân tích' : '✅ Analyzed';

        document.querySelector('.code-input-section').style.display = 'none';
        codeInfo.style.display = 'block';
        codeQuickActions.style.display = 'block';

        codeWelcome.style.display = 'none';
        codeChatMessages.style.display = 'flex';
        codeChatMessages.innerHTML = '';

        addCodeMessage('assistant', data.greeting);
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

async function clearCodeSession() {
    if (state.code.sessionId) {
        try { await fetch(`/api/code/session/${state.code.sessionId}/clear`, { method: 'POST' }); } catch (e) { }
    }
    state.code.sessionId = null;
    state.code.codename = null;
    codeInfo.style.display = 'none';
    codeQuickActions.style.display = 'none';
    document.querySelector('.code-input-section').style.display = 'block';
    codeInput.value = '';
    codeChatMessages.style.display = 'none';
    codeChatMessages.innerHTML = '';
    codeWelcome.style.display = 'flex';
    updateChatInput();
    showToast('🔄', state.language === 'vi' ? 'Đã xóa. Paste code mới.' : 'Cleared. Paste new code.');
}

function addCodeMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = `
        <div class="message-avatar"><span class="material-symbols-rounded">${role === 'assistant' ? 'smart_toy' : 'person'}</span></div>
        <div class="message-bubble">${formatMessage(content)}</div>
    `;
    codeChatMessages.appendChild(msgDiv);
    codeChatMessages.scrollTop = codeChatMessages.scrollHeight;
}
