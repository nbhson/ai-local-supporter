// ===== STATE =====
const state = {
    activeTab: 'doc',
    language: 'en', // Default to English
    doc: { sessionId: null, filename: null, model: null, isProcessing: false },
    code: { sessionId: null, codename: null, model: null, isProcessing: false },
    chat: { sessionId: null, model: null, isProcessing: false },
    project: {
        sessionId: null,
        path: null,
        isLocal: false,
        tree: null,
        stats: null,
        openFiles: {}, // { relPath: content }
        activeFile: null,
        selectedFiles: new Set(),
        isProcessing: false,
        diffOriginalContent: null,
        diffProposedContent: null,
        diffFilePath: null
    }
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

// Project Tab DOM Refs
const projectPathInput = $('projectPathInput');
const openLocalProjectBtn = $('openLocalProjectBtn');
const projectUploadArea = $('projectUploadArea');
const projectFolderInput = $('projectFolderInput');
const projectExplorerSection = $('projectExplorerSection');
const projectTreeContainer = $('projectTreeContainer');
const closeProjectBtn = $('closeProjectBtn');
const reloadProjectBtn = $('reloadProjectBtn');
const projectWorkspaceContainer = $('projectWorkspaceContainer');
const projectWelcome = $('projectWelcome');
const editorTabsBar = $('editorTabsBar');
const projectDashboard = $('projectDashboard');
const editorActiveView = $('editorActiveView');
const activeFileTitle = $('activeFileTitle');
const saveActiveFileBtn = $('saveActiveFileBtn');
const editorLineNumbers = $('editorLineNumbers');
const monacoEditorContainer = $('monacoEditorContainer');
const editorDiffView = $('editorDiffView');
const discardDiffBtn = $('discardDiffBtn');
const acceptDiffBtn = $('acceptDiffBtn');
const diffContainerViewport = $('diffContainerViewport');
const projectChatMessages = $('projectChatMessages');
const workspaceContextBar = $('workspaceContextBar');
const workspaceContextCount = $('workspaceContextCount');
const contextFilesTags = $('contextFilesTags');
const projectChatInput = $('projectChatInput');
const projectSendBtn = $('projectSendBtn');
const statTotalFiles = $('statTotalFiles');
const statTotalSize = $('statTotalSize');
const statMainLang = $('statMainLang');
const langsProgressContainer = $('langsProgressContainer');
const dashboardPathLabel = $('dashboardPathLabel');
