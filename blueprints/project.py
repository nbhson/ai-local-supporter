import os
import uuid
import json
import logging
from flask import Blueprint, request, jsonify, Response

import config
from services.database import db
from services.models import ProjectSession, ChatMessage
from services.ollama_service import call_ollama

project_bp = Blueprint('project', __name__)

EXCLUDE_DIRS = {'.git', 'node_modules', '.venv', 'venv', 'env', '.idea', '__pycache__', 'dist', 'build', 'target', '.npm', '.cache'}
EXCLUDE_FILES = {'.DS_Store', 'Thumbs.db'}

def get_project_stats(project_path):
    total_files = 0
    total_size = 0
    lang_stats = {}
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for f in files:
            if f in EXCLUDE_FILES:
                continue
            full_path = os.path.join(root, f)
            try:
                size = os.path.getsize(full_path)
                total_size += size
                total_files += 1
                
                _, ext = os.path.splitext(f)
                ext = ext.lower().strip('.')
                if not ext:
                    ext = 'plain text' if f.startswith('.') or f in ('LICENSE', 'Makefile', 'Dockerfile') else 'unknown'
                lang_stats[ext] = lang_stats.get(ext, 0) + 1
            except Exception:
                pass
                
    return {
        "total_files": total_files,
        "total_size": total_size,
        "lang_stats": lang_stats
    }

def scan_directory(current_path, base_path):
    tree = []
    try:
        entries = sorted(os.scandir(current_path), key=lambda e: (not e.is_dir(), e.name.lower()))
        for entry in entries:
            if entry.is_dir():
                if entry.name in EXCLUDE_DIRS:
                    continue
                tree.append({
                    "name": entry.name,
                    "path": os.path.relpath(entry.path, base_path),
                    "is_dir": True,
                    "children": scan_directory(entry.path, base_path)
                })
            else:
                if entry.name in EXCLUDE_FILES:
                    continue
                tree.append({
                    "name": entry.name,
                    "path": os.path.relpath(entry.path, base_path),
                    "is_dir": False
                })
    except Exception as e:
        logging.error(f"Error scanning directory {current_path}: {e}")
    return tree

@project_bp.route('/init', methods=['POST'])
def init_project():
    data = request.json or {}
    local_path = data.get('path', '').strip()
    model = data.get('model', config.DEFAULT_MODEL)
    ui_language = data.get('language', 'en')
    
    session_id = uuid.uuid4().hex
    
    if local_path:
        # Check if local path exists
        if not os.path.exists(local_path):
            return jsonify({"error": f"Thư mục không tồn tại: {local_path}" if ui_language == 'vi' else f"Directory does not exist: {local_path}"}), 400
        if not os.path.isdir(local_path):
            return jsonify({"error": f"Đường dẫn không phải là thư mục: {local_path}" if ui_language == 'vi' else f"Path is not a directory: {local_path}"}), 400
            
        try:
            stats = get_project_stats(local_path)
            tree = scan_directory(local_path, local_path)
            
            session = ProjectSession(
                session_id=session_id,
                project_path=local_path,
                is_local=True,
                status='ready',
                model=model,
                ui_language=ui_language
            )
            db.session.add(session)
            db.session.commit()
            
            return jsonify({
                "session_id": session_id,
                "is_local": True,
                "tree": tree,
                "stats": stats
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # Browser upload flow initialization
        session = ProjectSession(
            session_id=session_id,
            is_local=False,
            status='init',
            model=model,
            ui_language=ui_language
        )
        db.session.add(session)
        db.session.commit()
        return jsonify({
            "session_id": session_id,
            "is_local": False
        })

@project_bp.route('/<session_id>/upload', methods=['POST'])
def upload_project_files(session_id):
    session = ProjectSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
        
    files = request.files.getlist('files[]')
    paths = request.form.getlist('paths[]')
    
    if not files:
        return jsonify({"error": "No files uploaded"}), 400
        
    project_dir = os.path.join(config.UPLOAD_FOLDER, 'projects', session_id)
    os.makedirs(project_dir, exist_ok=True)
    
    try:
        for file, path in zip(files, paths):
            # Clean up paths to ensure no path traversal vulnerability
            # webkitRelativePath format is "root-folder-name/sub-folder/file.txt"
            parts = path.split('/')
            if len(parts) > 1:
                # Strip the root folder name from relative path to keep structure cleaner
                rel_path = os.path.join(*parts[1:])
            else:
                rel_path = path
                
            # Exclude folders
            skip = False
            for part in parts:
                if part in EXCLUDE_DIRS:
                    skip = True
                    break
            if skip:
                continue
                
            dest_filepath = os.path.join(project_dir, rel_path)
            os.makedirs(os.path.dirname(dest_filepath), exist_ok=True)
            file.save(dest_filepath)
            
        session.project_path = project_dir
        session.status = 'ready'
        db.session.commit()
        
        stats = get_project_stats(project_dir)
        tree = scan_directory(project_dir, project_dir)
        
        return jsonify({
            "success": True,
            "tree": tree,
            "stats": stats
        })
    except Exception as e:
        session.status = 'failed'
        db.session.commit()
        logging.exception("Error in project upload")
        return jsonify({"error": str(e)}), 500

@project_bp.route('/<session_id>/file', methods=['GET'])
def get_project_file(session_id):
    session = ProjectSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
        
    rel_path = request.args.get('path', '').strip()
    if not rel_path:
        return jsonify({"error": "File path is required"}), 400
        
    # Prevent directory traversal
    if '..' in rel_path or rel_path.startswith('/'):
        return jsonify({"error": "Invalid file path"}), 400
        
    filepath = os.path.join(session.project_path, rel_path)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    if os.path.isdir(filepath):
        return jsonify({"error": "Path is a directory, not a file"}), 400
        
    try:
        # Read text content safely
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        return jsonify({
            "path": rel_path,
            "name": os.path.basename(rel_path),
            "content": content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@project_bp.route('/<session_id>/write_file', methods=['POST'])
def write_project_file(session_id):
    session = ProjectSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
        
    data = request.json or {}
    rel_path = data.get('path', '').strip()
    content = data.get('content', '')
    
    if not rel_path:
        return jsonify({"error": "File path is required"}), 400
    if '..' in rel_path or rel_path.startswith('/'):
        return jsonify({"error": "Invalid file path"}), 400
        
    filepath = os.path.join(session.project_path, rel_path)
    try:
        # Create directories if writing a new file
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"success": True, "path": rel_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@project_bp.route('/<session_id>/scan', methods=['GET'])
def rescan_project(session_id):
    session = ProjectSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    try:
        stats = get_project_stats(session.project_path)
        tree = scan_directory(session.project_path, session.project_path)
        return jsonify({
            "tree": tree,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@project_bp.route('/<session_id>/chat', methods=['POST'])
def chat_project(session_id):
    session = ProjectSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
        
    data = request.json or {}
    question = data.get('question', '').strip()
    active_file = data.get('active_file', '').strip()
    selected_files = data.get('selected_files', [])
    language = data.get('language', 'en')
    model = data.get('model', session.model or config.DEFAULT_MODEL)
    
    if not question:
        return jsonify({"error": "Question is empty"}), 400
        
    lang_instruction = "Respond in English." if language == "en" else "Respond in Vietnamese."
    
    system_prompt = f"""You are a professional software engineer and an expert AI Coding Assistant.
You are helping the user work on a programming project.
{lang_instruction}

When providing code updates, optimizations, or generating new code:
1. Always write the FULL updated code or a CLEAR chunk inside code blocks with correct language syntax identifiers.
2. Put clear instructions.
3. If you suggest modifying an existing active file, the client will display "Compare" and "Apply" buttons.
4. If you suggest CREATING a new file, you MUST write a tag like [CREATE_FILE: path/to/file.ext] directly before the code block.
   Example:
   [CREATE_FILE: src/utils.js]
   ```javascript
   // code content
   ```
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Read the active file and selected files as context
    context_text = ""
    files_to_read = set()
    if active_file:
        files_to_read.add(active_file)
    if selected_files:
        files_to_read.update(selected_files)
        
    for rel_path in files_to_read:
        if '..' in rel_path or rel_path.startswith('/'):
            continue
        filepath = os.path.join(session.project_path, rel_path)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    file_content = f.read()
                # Limit size per file context to avoid blowing up context window (max 30k chars per file)
                if len(file_content) > 30000:
                    file_content = file_content[:30000] + "\n\n...[file truncated due to length]"
                context_text += f"\n\n--- File: {rel_path} ---\n{file_content}\n---------------------\n"
            except Exception as e:
                logging.warning(f"Could not load file context {rel_path}: {e}")
                
    if context_text:
        messages.append({
            "role": "system", 
            "content": f"Here is the context of files from the workspace:\n{context_text}"
        })
        
    # Retrieve chat history (max 8 messages)
    chat_history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()
    for msg in chat_history[-8:]:
        messages.append({"role": msg.role, "content": msg.content})
        
    # Save user message to history
    user_msg = ChatMessage(session_id=session_id, role='user', content=question)
    db.session.add(user_msg)
    db.session.commit()
    
    # Append user question
    messages.append({"role": "user", "content": question})
    
    def generate():
        from app import app
        with app.app_context():
            generator = call_ollama(messages, model, stream=True)
            full_answer = ""
            for chunk in generator:
                if chunk.startswith("data: "):
                    data_str = chunk[6:].strip()
                    if data_str != "[DONE]":
                        try:
                            data_json = json.loads(data_str)
                            if "content" in data_json:
                                full_answer += data_json["content"]
                        except:
                            pass
                yield chunk
            
            # Save AI answer to database
            assistant_msg = ChatMessage(session_id=session_id, role='assistant', content=full_answer)
            db.session.add(assistant_msg)
            db.session.commit()
            
    return Response(generate(), mimetype='text/event-stream')
