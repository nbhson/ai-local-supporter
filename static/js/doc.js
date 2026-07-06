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
    showToast('🔄', state.language === 'vi' ? 'Đã xóa. Upload file mới.' : 'Cleared. Upload new file.');
}
