// ===== INIT =====
async function init() {
    await loadModels();
    setupEventListeners();
    initProjectWorkspace();
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
    if (tab === 'project') {
        chatInputContainer.style.display = 'none';
        return;
    }
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
        projectTab: 'Projects',
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
        welcomeChatDesc: 'Ask anything you want with AI',
        welcomeProject: 'Project Workspace',
        welcomeProjectDesc: 'Open or upload a folder to browse and generate code'
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
        projectTab: 'Dự án',
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
        welcomeChatDesc: 'Hỏi bất cứ điều gì bạn muốn với AI',
        welcomeProject: 'Không gian Dự án',
        welcomeProjectDesc: 'Mở hoặc upload một thư mục để duyệt code và sinh code'
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
    const projectTabBtn = document.querySelector('[data-tab="project"] .tab-label');
    if (projectTabBtn) projectTabBtn.textContent = t.projectTab;

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

    const projWelcomeH2 = document.querySelector('#projectWelcome h2');
    const projWelcomeP = document.querySelector('#projectWelcome p');
    if (projWelcomeH2) projWelcomeH2.textContent = t.welcomeProject;
    if (projWelcomeP) projWelcomeP.textContent = t.welcomeProjectDesc;

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

// ===== START =====
init();
