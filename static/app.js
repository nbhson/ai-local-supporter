// ===== STATE =====
const state = {
    activeTab: 'doc',
    language: 'en', // Default to English
    doc: { sessionId: null, filename: null, model: null, isProcessing: false },
    code: { sessionId: null, codename: null, model: null, isProcessing: false },
    chat: { sessionId: null, model: null, isProcessing: false }
};

// ===== DOM REFS =====
const $ = id => document.getElementById(id);
const uploadArea = $('uploadArea');
const fileInput = $('fileInput');
const modelSelect = $('modelSelect');
const languageSelect = $('languageSelect');
const uploadProgress = $('uploadProgress');
const progressFill = $('progressFill');
const progressText = $('progressText');
const fileInfo = $('fileInfoList');
const clearSessionBtn = $('clearSessionBtn');
const quickActions = $('quickActions');
const docWelcome = $('docWelcome');
const docChatMessages = $('docChatMessages');
const codeInput = $('codeInput');
const codeLanguage = $('codeLanguage');
const analyzeCodeBtn = $('analyzeCodeBtn');
const codeInfo = $('codeInfo');
const codeFileName = $('codeFileName');
const codeStatus = $('codeStatus');
const clearCodeSessionBtn = $('clearCodeSessionBtn');
const codeQuickActions = $('codeQuickActions');
const codeWelcome = $('codeWelcome');
const codeChatMessages = $('codeChatMessages');
const chatInputContainer = $('chatInputContainer');
const chatInput = $('chatInput');
const sendBtn = $('sendBtn');
const toast = $('toast');
const toastIcon = $('toastIcon');
const toastMessage = $('toastMessage');

// Free Chat DOM Refs
const chatWelcome = $('chatWelcome');
const chatChatMessages = $('chatChatMessages');
const chatQuickActions = $('chatQuickActions');
const clearChatSessionBtn = $('clearChatSessionBtn');
const chatStatus = $('chatStatus');

// ===== INIT =====
async function init() {
    await loadModels();
    setupEventListeners();
    updateUILanguage(); // Set default language on page load
}

async function loadModels() {
    try {
        const res = await fetch('/api/models');
        const data = await res.json();
        if (data.models && data.models.length > 0) {
            modelSelect.innerHTML = data.models.map(m => {
                const lowerM = m.toLowerCase();
                const isEmbedding = lowerM.includes('embed') || lowerM.includes('minilm') || lowerM.includes('bge-');
                return `<option value="${m}" ${isEmbedding ? 'disabled style="color: #888; font-style: italic; background-color: #222;"' : ''}>${m}${isEmbedding ? ' (embedding)' : ''}</option>`;
            }).join('');

            // Select the first non-disabled option by default
            const enabledOptions = Array.from(modelSelect.options).filter(opt => !opt.disabled);
            if (enabledOptions.length > 0) {
                modelSelect.value = enabledOptions[0].value;
                if (!state.doc.model) state.doc.model = modelSelect.value;
                if (!state.code.model) state.code.model = modelSelect.value;
                if (!state.chat.model) state.chat.model = modelSelect.value;
            }
        }
    } catch (e) {
        console.warn('Could not load models:', e);
    }
}

// ===== TAB SWITCHING =====
async function switchTab(tab) {
    state.activeTab = tab;

    // Sidebar tabs
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    document.querySelectorAll('.sidebar .tab-content').forEach(c => c.classList.toggle('active', c.id === `tab-${tab}`));

    // Main content tabs
    document.querySelectorAll('.main-tab').forEach(c => c.classList.toggle('active', c.id === `main-tab-${tab}`));

    // Close mobile sidebar on tab change
    const sidebar = document.querySelector('.sidebar');
    const overlay = $('sidebarOverlay');
    if (sidebar && overlay) {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
    }

    // Auto initialize chat session if switching to chat and no session exists
    if (tab === 'chat' && !state.chat.sessionId) {
        await initChatSession();
    }

    // Update chat input
    updateChatInput();
}

function updateChatInput() {
    const tab = state.activeTab;
    const s = tab === 'doc' ? state.doc : (tab === 'code' ? state.code : state.chat);
    const hasSession = tab === 'chat' ? !!state.chat.sessionId : (tab === 'doc' ? !!state.doc.sessionId : !!state.code.sessionId);
    const t = translations[state.language];

    if (hasSession) {
        chatInputContainer.style.display = 'block';
        chatInput.disabled = false;
        sendBtn.disabled = false;
        if (tab === 'chat') {
            chatInput.placeholder = t.chatPlaceholder;
        } else {
            chatInput.placeholder = tab === 'doc'
                ? t.docChatPlaceholder
                : t.codeChatPlaceholder;
        }
        chatInput.focus();
    } else {
        chatInputContainer.style.display = 'none';
        chatInput.disabled = true;
        sendBtn.disabled = true;
    }
}

// ===== EVENT LISTENERS =====
function setupEventListeners() {
    // Mobile sidebar toggle
    const toggleBtn = $('mobileSidebarToggle');
    const sidebarOverlay = $('sidebarOverlay');
    const sidebar = document.querySelector('.sidebar');

    if (toggleBtn && sidebarOverlay && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            sidebarOverlay.classList.toggle('show');
        });

        sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('show');
        });
    }

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Language change
    languageSelect.addEventListener('change', (e) => {
        state.language = e.target.value;
        updateUILanguage();
    });

    // Upload
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) handleFileUploads(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFileUploads(e.target.files);
    });

    // Chat
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    chatInput.addEventListener('input', autoResizeTextarea);

    // Clear sessions
    clearSessionBtn.addEventListener('click', clearDocSession);
    clearCodeSessionBtn.addEventListener('click', clearCodeSession);
    clearChatSessionBtn.addEventListener('click', clearChatSession);

    // Code analyze
    analyzeCodeBtn.addEventListener('click', analyzeCode);
    codeInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) analyzeCode();
    });

    // Quick actions - doc
    document.querySelectorAll('#tab-doc .quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            chatInput.value = btn.dataset.question;
            sendMessage();
        });
    });

    // Quick actions - code
    document.querySelectorAll('#tab-code .quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            chatInput.value = btn.dataset.codeQuestion;
            sendMessage();
        });
    });

    // Quick actions - chat
    document.querySelectorAll('#tab-chat .quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            chatInput.value = btn.dataset.chatQuestion;
            sendMessage();
        });
    });
}

// ===== DOCUMENT UPLOAD =====
async function handleFileUploads(files) {
    if (files.length === 0) return;
    if (files.length > 3) {
        showToast('⚠️', state.language === 'vi' ? 'Tối đa 3 files được phép tải lên.' : 'Maximum of 3 files allowed.');
        return;
    }

    // Verify size of each file
    for (let i = 0; i < files.length; i++) {
        if (files[i].size > 50 * 1024 * 1024) {
            showToast('⚠️', state.language === 'vi' ? `File "${files[i].name}" quá lớn. Giới hạn 50MB.` : `File "${files[i].name}" is too large. Limit 50MB.`);
            return;
        }
    }

    state.doc.model = modelSelect.value;

    uploadArea.style.display = 'none';
    uploadProgress.style.display = 'block';
    progressFill.style.width = '10%';
    progressText.textContent = state.language === 'vi' ? `Đang tải lên ${files.length} file...` : `Uploading ${files.length} files...`;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    formData.append('model', state.doc.model);
    formData.append('language', state.language);

    try {
        const res = await fetch('/api/doc/upload', {
            method: 'POST',
            headers: {
                'Accept': 'application/json'
            },
            body: formData
        });

        const uploadData = await res.json();
        if (!res.ok) throw new Error(uploadData.error || 'Upload failed');

        const sessionId = uploadData.session_id;
        state.doc.sessionId = sessionId;

        // Start polling document processing status
        let attempts = 0;
        const maxAttempts = 180; // 6 minutes timeout for 3 files

        while (attempts < maxAttempts) {
            const statusRes = await fetch(`/api/doc/status/${sessionId}`);
            if (!statusRes.ok) {
                const statusErr = await statusRes.json();
                throw new Error(statusErr.error || 'Failed to check status');
            }

            const statusData = await statusRes.json();

            if (statusData.status === 'ready') {
                state.doc.filename = statusData.filename;
                progressFill.style.width = '100%';
                progressText.textContent = state.language === 'vi' ? '✅ Hoàn tất!' : '✅ Completed!';

                setTimeout(() => {
                    uploadProgress.style.display = 'none';
                    showDocFileInfo(statusData);

                    docWelcome.style.display = 'none';
                    docChatMessages.style.display = 'flex';
                    docChatMessages.innerHTML = '';

                    addDocMessage('assistant', statusData.greeting);
                    updateChatInput();
                }, 500);
                return;
            } else if (statusData.status === 'failed') {
                throw new Error(statusData.error || 'Processing failed');
            }

            attempts++;
            const pct = Math.min(95, 10 + attempts * 2);
            progressFill.style.width = `${pct}%`;
            progressText.textContent = state.language === 'vi'
                ? `Đang phân tích ${files.length} tài liệu với AI (${pct}%)...`
                : `Analyzing ${files.length} documents with AI (${pct}%)...`;

            await new Promise(resolve => setTimeout(resolve, 2000));
        }

        throw new Error(state.language === 'vi' ? 'Thời gian chờ xử lý file quá lâu.' : 'File processing timed out.');
    } catch (err) {
        progressFill.style.width = '100%';
        progressFill.style.background = '#ef4444';
        progressText.textContent = (state.language === 'vi' ? '❌ Lỗi: ' : '❌ Error: ') + err.message;
        showToast('❌', err.message);
        setTimeout(() => {
            uploadProgress.style.display = 'none';
            uploadArea.style.display = 'block';
            progressFill.style.background = 'var(--primary-color)';
        }, 3000);
    }
}

function showDocFileInfo(data) {
    const fileList = $('fileList');
    fileList.innerHTML = '';

    const files = data.files || [];
    if (files.length === 0) {
        files.push({
            filename: data.filename || 'document',
            file_type: data.file_type || 'document',
            status: data.status || 'ready'
        });
    }

    files.forEach(f => {
        const isImage = f.file_type === 'image';
        const fileItem = document.createElement('div');
        fileItem.className = 'file-info';
        fileItem.style.marginTop = '0';

        const statusText = f.status === 'ready'
            ? (state.language === 'vi' ? '✅ Đã phân tích' : '✅ Analyzed')
            : (f.status === 'failed'
                ? (state.language === 'vi' ? `❌ Lỗi: ${f.error || 'Thất bại'}` : `❌ Error: ${f.error || 'Failed'}`)
                : (state.language === 'vi' ? '⏳ Đang xử lý' : '⏳ Processing'));

        fileItem.innerHTML = `
            <div class="file-icon">
                <span class="material-symbols-rounded">${isImage ? 'image' : 'description'}</span>
            </div>
            <div class="file-details">
                <p class="file-name" title="${f.filename}">${f.filename}</p>
                <p class="file-status" style="color: ${f.status === 'ready' ? 'var(--success)' : (f.status === 'failed' ? 'var(--error)' : 'var(--text-secondary)')}">${statusText}</p>
            </div>
        `;

        console.log("Binding click for:", f.filename, "isImage:", isImage, "status:", f.status, "unique_filename:", f.unique_filename);
        if (isImage && f.status === 'ready' && f.unique_filename) {
            fileItem.style.cursor = 'pointer';
            fileItem.title = state.language === 'vi' ? 'Click để xem ảnh' : 'Click to view image';
            fileItem.addEventListener('click', () => {
                console.log("File card clicked! Calling openModal for:", f.unique_filename);
                openModal(`/api/doc/files/${f.unique_filename}`, f.filename);
            });
        }

        fileList.appendChild(fileItem);
    });

    fileInfo.style.display = 'flex';
    quickActions.style.display = 'block';
    uploadArea.style.display = 'none';
}

function addDocMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = `
        <div class="message-avatar"><span class="material-symbols-rounded">${role === 'assistant' ? 'smart_toy' : 'person'}</span></div>
        <div class="message-bubble">${formatMessage(content)}</div>
    `;
    docChatMessages.appendChild(msgDiv);
    docChatMessages.scrollTop = docChatMessages.scrollHeight;
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

function formatMessage(text) {
    if (!text) return "";

    // Handle DeepSeek <think> tag
    let formatted = text.replace(/<think>([\s\S]*?)<\/think>/g, '<div class="thought-process"><div class="thought-header"><span class="material-symbols-rounded">psychology</span> Thought Process</div><div class="thought-content">$1</div></div>');

    // Handle unclosed <think> tag during streaming
    if (formatted.includes('<think>') && !formatted.includes('</think>')) {
        formatted = formatted.replace(/<think>([\s\S]*)/, '<div class="thought-process"><div class="thought-header"><span class="material-symbols-rounded spinning">progress_activity</span> Thinking...</div><div class="thought-content">$1</div></div>');
    }

    // Handle code blocks with copy-code button
    formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        const escapedCode = code
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
        return `<div class="code-block-wrapper">
            <div class="code-header">
                <span>${lang || 'code'}</span>
                <button class="copy-code-btn" onclick="copyCodeToClipboard(this)" data-code="${escapedCode}" title="Copy Code">
                    <span class="material-symbols-rounded">content_copy</span>
                </button>
            </div>
            <pre><code>${code}</code></pre>
        </div>`;
    });

    return formatted
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

// Global copy to clipboard function
window.copyCodeToClipboard = (btn) => {
    const code = btn.getAttribute('data-code');
    const txt = document.createElement('textarea');
    txt.innerHTML = code;
    const decodedCode = txt.value;

    navigator.clipboard.writeText(decodedCode).then(() => {
        const icon = btn.querySelector('.material-symbols-rounded');
        icon.textContent = 'check';
        btn.classList.add('copied');
        showToast('✅', state.language === 'vi' ? 'Đã copy code vào clipboard!' : 'Copied code to clipboard!');
        setTimeout(() => {
            icon.textContent = 'content_copy';
            btn.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        showToast('❌', 'Failed to copy: ' + err);
    });
};

function showTypingIndicator(target) {
    const el = document.createElement('div');
    el.className = 'message assistant typing';
    el.id = 'typingIndicator';
    el.innerHTML = `
        <div class="message-avatar"><span class="material-symbols-rounded">smart_toy</span></div>
        <div class="message-bubble typing-bubble">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
    `;
    target.appendChild(el);
    target.scrollTop = target.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

// ===== CODE ANALYSIS =====
async function analyzeCode() {
    const code = codeInput.value.trim();
    if (!code) {
        showToast('⚠️', 'Vui lòng paste code trước!');
        return;
    }

    state.code.model = modelSelect.value;
    analyzeCodeBtn.disabled = true;
    analyzeCodeBtn.textContent = '⏳ Đang phân tích...';

    try {
        const res = await fetch('/api/code/analyze', {
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
        state.code.codename = `code.${codeLanguage.value}`;

        // Show code info
        codeFileName.textContent = `code.${codeLanguage.value}`;
        codeStatus.textContent = '✅ Đã phân tích';
        codeInfo.style.display = 'block';
        codeQuickActions.style.display = 'block';
        document.querySelector('.code-input-section').style.display = 'none';

        // Show analysis container
        codeWelcome.style.display = 'none';
        codeChatMessages.style.display = 'flex';
        codeChatMessages.innerHTML = '';

        addCodeMessage('assistant', data.greeting);
        updateChatInput();

        showToast('✅', 'Phân tích code thành công!');
    } catch (err) {
        showToast('❌', err.message);
    } finally {
        analyzeCodeBtn.disabled = false;
        const t = translations[state.language];
        analyzeCodeBtn.innerHTML = `<span class="material-symbols-rounded btn-icon-left">analytics</span> ${t.analyzeCode}`;
    }
}

// ===== SEND MESSAGE =====
async function sendMessage() {
    const question = chatInput.value.trim();
    if (!question) return;

    const tab = state.activeTab;
    const isDoc = tab === 'doc';
    const isCode = tab === 'code';
    const isChat = tab === 'chat';
    const s = isDoc ? state.doc : (isCode ? state.code : state.chat);

    if (s.isProcessing || !s.sessionId) return;
    s.isProcessing = true;

    chatInput.disabled = true;
    sendBtn.disabled = true;

    const targetMessages = isDoc ? docChatMessages : (isCode ? codeChatMessages : chatChatMessages);
    const addMsg = isDoc ? addDocMessage : (isCode ? addCodeMessage : addChatMessage);

    addMsg('user', question);
    chatInput.value = '';
    autoResizeTextarea();
    showTypingIndicator(targetMessages);

    try {
        const endpoint = isDoc ? '/api/doc/chat' : (isCode ? '/api/code/chat' : '/api/chat/chat');
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: s.sessionId,
                question: question,
                model: modelSelect.value,
                language: state.language
            })
        });

        removeTypingIndicator();

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.error || 'Chat failed');
        }

        // create bubble for assistant
        const msgDiv = document.createElement('div');
        msgDiv.className = `message assistant`;
        msgDiv.innerHTML = `
            <div class="message-avatar"><span class="material-symbols-rounded">smart_toy</span></div>
            <div class="message-bubble"></div>
        `;
        targetMessages.appendChild(msgDiv);
        const bubble = msgDiv.querySelector('.message-bubble');

        await readStream(res, bubble, '');
    } catch (err) {
        removeTypingIndicator();
        const msgDiv = document.createElement('div');
        msgDiv.className = `message assistant`;
        msgDiv.innerHTML = `
            <div class="message-avatar"><span class="material-symbols-rounded">smart_toy</span></div>
            <div class="message-bubble">${formatMessage(`❌ **Lỗi:** ${err.message}`)}</div>
        `;
        targetMessages.appendChild(msgDiv);
        showToast('❌', err.message);
    } finally {
        s.isProcessing = false;
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// ===== SESSION MANAGEMENT =====
async function clearDocSession() {
    if (state.doc.sessionId) {
        try { await fetch(`/api/doc/session/${state.doc.sessionId}/clear`, { method: 'POST' }); } catch (e) { }
    }
    state.doc.sessionId = null;
    state.doc.filename = null;
    fileInfo.style.display = 'none';
    quickActions.style.display = 'none';
    uploadArea.style.display = 'block';
    docChatMessages.style.display = 'none';
    docChatMessages.innerHTML = '';
    docWelcome.style.display = 'flex';
    updateChatInput();
    showToast('🔄', 'Đã xóa. Upload file mới.');
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
    showToast('🔄', 'Đã xóa. Paste code mới.');
}

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

// ===== LANGUAGE MANAGEMENT =====
const translations = {
    en: {
        uploadText: 'Drag & drop files here',
        uploadSubtext: 'or click to select files',
        uploadFormats: 'PDF, DOCX, TXT, MD, PNG, JPG, ...',
        processing: 'Processing...',
        analyzing: 'Analyzing with AI...',
        completed: '✅ Complete!',
        analyzed: '✅ Analyzed',
        docTab: 'Documents',
        codeTab: 'Code',
        chatTab: 'Chat',
        pasteCode: 'Paste your code here',
        analyzeCode: 'Analyze Code',
        analyzingCode: '⏳ Analyzing...',
        chatPlaceholder: 'Type your question...',
        docChatPlaceholder: 'Ask about the document...',
        codeChatPlaceholder: 'Ask about the code...',
        uploadError: 'File too large. Limit 50MB.',
        selectFileError: 'Please select a file first!',
        clearSession: 'Cleared. Upload new file.',
        clearCodeSession: 'Cleared. Paste new code.',
        clearChatSession: 'Cleared chat history.',
        welcomeDoc: 'Document Analysis',
        welcomeDocDesc: 'Upload files to analyze and ask questions',
        welcomeCode: 'Code Analysis',
        welcomeCodeDesc: 'Paste code in sidebar to analyze and ask questions',
        welcomeChat: 'Free Chat',
        welcomeChatDesc: 'Ask anything you want with AI'
    },
    vi: {
        uploadText: 'Kéo thả file vào đây',
        uploadSubtext: 'hoặc click để chọn file',
        uploadFormats: 'PDF, DOCX, TXT, MD, PNG, JPG, ...',
        processing: 'Đang xử lý...',
        analyzing: 'Đang phân tích với AI...',
        completed: '✅ Hoàn tất!',
        analyzed: '✅ Đã phân tích',
        docTab: 'Tài liệu',
        codeTab: 'Code',
        chatTab: 'Trò chuyện',
        pasteCode: 'Dán code của bạn vào đây',
        analyzeCode: 'Phân tích Code',
        analyzingCode: '⏳ Đang phân tích...',
        chatPlaceholder: 'Nhập câu hỏi...',
        docChatPlaceholder: 'Nhập câu hỏi về tài liệu...',
        codeChatPlaceholder: 'Nhập câu hỏi về code...',
        uploadError: 'File quá lớn. Giới hạn 50MB.',
        selectFileError: 'Vui lòng paste code trước!',
        clearSession: 'Đã xóa. Upload file mới.',
        clearCodeSession: 'Đã xóa. Paste code mới.',
        clearChatSession: 'Đã xóa lịch sử chat.',
        welcomeDoc: 'Phân tích tài liệu',
        welcomeDocDesc: 'Upload file để phân tích và đặt câu hỏi',
        welcomeCode: 'Phân tích Code',
        welcomeCodeDesc: 'Dán code vào sidebar để phân tích và đặt câu hỏi',
        welcomeChat: 'Trò chuyện tự do',
        welcomeChatDesc: 'Hỏi bất cứ điều gì bạn muốn với AI'
    }
};

function updateUILanguage() {
    const lang = state.language;
    const t = translations[lang];

    // Update upload area
    document.querySelector('.upload-text').textContent = t.uploadText;
    document.querySelector('.upload-subtext').textContent = t.uploadSubtext;
    document.querySelector('.upload-formats').textContent = t.uploadFormats;

    // Update tab labels
    document.querySelector('[data-tab="doc"] .tab-label').textContent = t.docTab;
    document.querySelector('[data-tab="code"] .tab-label').textContent = t.codeTab;
    document.querySelector('[data-tab="chat"] .tab-label').textContent = t.chatTab;

    // Update code section
    document.querySelector('.code-textarea').placeholder = t.pasteCode;
    analyzeCodeBtn.innerHTML = `<span class="material-symbols-rounded btn-icon-left">analytics</span> ${t.analyzeCode}`;

    // Update welcome screens
    document.querySelector('#docWelcome h2').textContent = t.welcomeDoc;
    document.querySelector('#docWelcome p').textContent = t.welcomeDocDesc;
    document.querySelector('#codeWelcome h2').textContent = t.welcomeCode;
    document.querySelector('#codeWelcome p').textContent = t.welcomeCodeDesc;
    document.querySelector('#chatWelcome h2').textContent = t.welcomeChat;
    document.querySelector('#chatWelcome p').textContent = t.welcomeChatDesc;

    // Update chat input placeholder
    updateChatInput();
}

// ===== UTILITIES =====
async function readStream(response, messageBubbleElement, prefixText = "") {
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let fullText = "";

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const container = messageBubbleElement.closest('.chat-messages');
        const threshold = 150;
        const wasAtBottom = container ? (container.scrollHeight - container.scrollTop - container.clientHeight < threshold) : false;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const dataStr = line.slice(6).trim();
                if (dataStr === '[DONE]') break;

                try {
                    const data = JSON.parse(dataStr);
                    if (data.content) {
                        fullText += data.content;
                        messageBubbleElement.innerHTML = formatMessage(prefixText + fullText);
                    } else if (data.error) {
                        messageBubbleElement.innerHTML = formatMessage(`❌ **Lỗi:** ${data.error}`);
                    }
                } catch (e) {
                    // ignore partial json
                }
            }
        }

        if (container && wasAtBottom) {
            container.scrollTop = container.scrollHeight;
        }
    }
}

function autoResizeTextarea() {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
}

function showToast(icon, message) {
    toastIcon.textContent = icon;
    toastMessage.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 4000);
}

// ===== IMAGE MODAL =====
const imageModal = $('imageModal');
const modalImg = $('modalImg');
const modalCaption = $('modalCaption');
const closeImageModal = $('closeImageModal');
console.log("Modal elements initialized:", { imageModal, modalImg, modalCaption, closeImageModal });

function openModal(imgUrl, caption) {
    console.log("openModal called with:", imgUrl, caption, "elements status:", { modalImg, modalCaption, imageModal });
    if (modalImg && modalCaption && imageModal) {
        modalImg.src = imgUrl;
        modalCaption.textContent = caption;
        imageModal.classList.add('show');
    }
}

function closeModal() {
    if (imageModal && modalImg) {
        imageModal.classList.remove('show');
        modalImg.src = '';
    }
}

if (closeImageModal) {
    closeImageModal.addEventListener('click', closeModal);
}
if (imageModal) {
    imageModal.addEventListener('click', (e) => {
        if (e.target === imageModal) closeModal();
    });
}
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && imageModal && imageModal.classList.contains('show')) {
        closeModal();
    }
});

// ===== START =====
init();
