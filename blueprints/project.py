import os
import uuid
import json
import logging
import re
import subprocess
import time
from flask import Blueprint, request, jsonify, Response

import config
from services.database import db
from services.models import ProjectSession
from services.agent_service import (
    scan_directory_and_stats, get_simple_tree_str, generate_agent_stream,
    get_cached_project_tree, set_cached_project_tree, invalidate_project_tree_cache
)
from services.errors import SessionNotFoundError, InvalidRequestError
from services.repositories import ProjectSessionRepository

project_bp = Blueprint('project', __name__)

EXCLUDE_DIRS = config.EXCLUDE_DIRS
EXCLUDE_FILES = config.EXCLUDE_FILES



@project_bp.route('/init', methods=['POST'])
def init_project():
    data = request.json or {}
    local_path = data.get('path', '').strip()
    model = data.get('model', config.DEFAULT_MODEL)
    ui_language = data.get('language', 'en')
    
    session_id = uuid.uuid4().hex
    
    if not local_path:
        # Browser upload flow initialization
        session = ProjectSession(
            session_id=session_id,
            is_local=False,
            status='init',
            model=model,
            ui_language=ui_language
        )
        ProjectSessionRepository.save(session)
        return jsonify({
            "session_id": session_id,
            "is_local": False
        })

    # Local path flow
    if not os.path.exists(local_path):
        error_msg = f"Thư mục không tồn tại: {local_path}" if ui_language == 'vi' else f"Directory does not exist: {local_path}"
        raise InvalidRequestError(error_msg)
    if not os.path.isdir(local_path):
        error_msg = f"Đường dẫn không phải là thư mục: {local_path}" if ui_language == 'vi' else f"Path is not a directory: {local_path}"
        raise InvalidRequestError(error_msg)
        
    try:
        tree, stats = scan_directory_and_stats(local_path, local_path)
        
        session = ProjectSession(
            session_id=session_id,
            project_path=local_path,
            is_local=True,
            status='ready',
            model=model,
            ui_language=ui_language
        )
        ProjectSessionRepository.save(session)
        
        return jsonify({
            "session_id": session_id,
            "is_local": True,
            "tree": tree,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route('/<session_id>/upload', methods=['POST'])
def upload_project_files(session_id):
    session = ProjectSessionRepository.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError()
        
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
        ProjectSessionRepository.save(session)
        
        tree, stats = scan_directory_and_stats(project_dir, project_dir)
        
        return jsonify({
            "success": True,
            "tree": tree,
            "stats": stats
        })
    except Exception as e:
        session.status = 'failed'
        ProjectSessionRepository.save(session)
        logging.exception("Error in project upload")
        return jsonify({"error": str(e)}), 500

@project_bp.route('/<session_id>/file', methods=['GET'])
def get_project_file(session_id):
    session = ProjectSessionRepository.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError()
        
    rel_path = request.args.get('path', '').strip()
    if not rel_path:
        raise InvalidRequestError("File path is required")
    if '..' in rel_path or rel_path.startswith('/'):
        raise InvalidRequestError("Invalid file path")
        
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
    session = ProjectSessionRepository.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError()
        
    data = request.json or {}
    rel_path = data.get('path', '').strip()
    content = data.get('content', '')
    
    if not rel_path:
        raise InvalidRequestError("File path is required")
    if '..' in rel_path or rel_path.startswith('/'):
        raise InvalidRequestError("Invalid file path")
        
    filepath = os.path.join(session.project_path, rel_path)
    try:
        # Create directories if writing a new file
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        invalidate_project_tree_cache(session_id)
        return jsonify({"success": True, "path": rel_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@project_bp.route('/<session_id>/scan', methods=['GET'])
def rescan_project(session_id):
    session = ProjectSessionRepository.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError()
    try:
        invalidate_project_tree_cache(session_id)
        tree, stats = scan_directory_and_stats(session.project_path, session.project_path)
        set_cached_project_tree(session_id, tree, stats)
        return jsonify({
            "tree": tree,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@project_bp.route('/<session_id>/chat', methods=['POST'])
def chat_project(session_id):
    session = ProjectSessionRepository.get_by_id(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    project_path = session.project_path
    data = request.json or {}
    question = data.get('question', '').strip()
    language = data.get('language', 'en')
    model = data.get('model', session.model or config.DEFAULT_MODEL)
    context_files = data.get('context_files', [])
    agent_mode = data.get('agent_mode', True)
    
    if not question:
        return jsonify({"error": "Question is empty"}), 400
        
    # Read context files content
    context_str = ""
    if context_files:
        context_str_parts = [
            "\nADDITIONAL CONTEXT FILES SELECTED BY USER:",
            "CRITICAL: The content of these files is ALREADY provided below. Do NOT output or repeat the code of these files in your response."
        ]
        for rel_path in context_files:
            if not rel_path or '..' in rel_path or rel_path.startswith('/'):
                continue
            filepath = os.path.join(project_path, rel_path)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    if len(content) > 15000:
                        content = content[:15000] + "\n\n...[content truncated to save context]..."
                    context_str_parts.append(f"\nFile: `{rel_path}`\n```\n{content}\n```")
                except Exception as e:
                    context_str_parts.append(f"\nFile: `{rel_path}` (Error reading content: {str(e)})")
        context_str = "\n".join(context_str_parts)

    # Get initial project tree (limit depth for context)
    tree_nodes, stats = get_cached_project_tree(session_id)
    if tree_nodes is None:
        tree_nodes, stats = scan_directory_and_stats(project_path, project_path)
        set_cached_project_tree(session_id, tree_nodes, stats)
    tree_str = "\n".join(get_simple_tree_str(tree_nodes))
    
    # Delegate stream generation to services/agent_service.py
    def stream_response():
        return generate_agent_stream(
            session_id=session_id,
            project_path=project_path,
            question=question,
            language=language,
            model=model,
            context_str=context_str,
            tree_str=tree_str,
            agent_mode=agent_mode
        )
        
    response = Response(stream_response(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response
