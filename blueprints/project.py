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
    scan_directory_and_stats, get_simple_tree_str, generate_agent_stream
)
from services.errors import SessionNotFoundError, InvalidRequestError
from services.repositories import ProjectSessionRepository

project_bp = Blueprint('project', __name__)

EXCLUDE_DIRS = {
    '.git', 'node_modules', '.venv', 'venv', 'env', '.idea', '__pycache__', 
    'dist', 'build', 'target', '.npm', '.cache', '.angular', '.next', '.nuxt',
    '.sass-cache', '.svelte-kit', '.agents', '.gemini', 'coverage', '.nyc_output'
}
EXCLUDE_FILES = {'.DS_Store', 'Thumbs.db'}

def scan_directory_and_stats(current_path, base_path, stats=None, current_depth=0, max_depth=None):
    if stats is None:
        stats = {
            "total_files": 0,
            "total_size": 0,
            "lang_stats": {}
        }
    tree = []
    if max_depth is not None and current_depth > max_depth:
        return tree, stats
    try:
        entries = sorted(os.scandir(current_path), key=lambda e: (not e.is_dir(), e.name.lower()))
        for entry in entries:
            if entry.is_dir():
                if entry.name in EXCLUDE_DIRS:
                    continue
                subtree, _ = scan_directory_and_stats(entry.path, base_path, stats, current_depth + 1, max_depth)
                tree.append({
                    "name": entry.name,
                    "path": os.path.relpath(entry.path, base_path),
                    "is_dir": True,
                    "children": subtree
                })
            else:
                if entry.name in EXCLUDE_FILES:
                    continue
                rel_path = os.path.relpath(entry.path, base_path)
                tree.append({
                    "name": entry.name,
                    "path": rel_path,
                    "is_dir": False
                })
                try:
                    size = entry.stat().st_size
                    stats["total_size"] += size
                    stats["total_files"] += 1
                    
                    _, ext = os.path.splitext(entry.name)
                    ext = ext.lower().strip('.')
                    if not ext:
                        ext = 'plain text' if entry.name.startswith('.') or entry.name in ('LICENSE', 'Makefile', 'Dockerfile') else 'unknown'
                    stats["lang_stats"][ext] = stats["lang_stats"].get(ext, 0) + 1
                except Exception:
                    pass
    except Exception as e:
        logging.error(f"Error scanning directory {current_path}: {e}")
    return tree, stats

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
        return jsonify({"success": True, "path": rel_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@project_bp.route('/<session_id>/scan', methods=['GET'])
def rescan_project(session_id):
    session = ProjectSessionRepository.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError()
    try:
        tree, stats = scan_directory_and_stats(session.project_path, session.project_path)
        return jsonify({
            "tree": tree,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_simple_tree_str(nodes, depth=0, max_depth=None, max_entries_per_dir=None):
    if max_depth is None:
        max_depth = config.AGENT_MAX_DEPTH
    if max_entries_per_dir is None:
        max_entries_per_dir = config.AGENT_MAX_ENTRIES_PER_DIR
    if depth > max_depth:
        return []
    lines = []
    for i, node in enumerate(nodes):
        if i >= max_entries_per_dir:
            lines.append(f"{'  ' * depth}... (and {len(nodes) - max_entries_per_dir} more items, use LIST_DIR tool to view)")
            break
            
        indent = "  " * depth
        if node.get("is_dir"):
            lines.append(f"{indent}📁 {node['name']}/")
            lines.extend(get_simple_tree_str(node.get("children", []), depth + 1, max_depth, max_entries_per_dir))
        else:
            lines.append(f"{indent}📄 {node['name']}")
    return lines

def parse_tool_call(text):
    # Match [FINISH]
    if '[FINISH]' in text:
        return {'tool': 'FINISH', 'args': {}}
        
    # Match [READ_FILE: path]
    read_match = re.search(r'\[READ_FILE:\s*([^\s\]]+)\]', text)
    if read_match:
        return {'tool': 'READ_FILE', 'args': {'path': read_match.group(1)}}
        
    # Match [LIST_DIR: path]
    list_match = re.search(r'\[LIST_DIR:\s*([^\s\]]+)\]', text)
    if list_match:
        return {'tool': 'LIST_DIR', 'args': {'path': list_match.group(1)}}
        
    # Match [SEARCH_FILES: query]
    search_match = re.search(r'\[SEARCH_FILES:\s*([^\]]+)\]', text)
    if search_match:
        return {'tool': 'SEARCH_FILES', 'args': {'query': search_match.group(1).strip()}}
        
    # Match [RUN_COMMAND: cmd]
    run_match = re.search(r'\[RUN_COMMAND:\s*([^\]]+)\]', text)
    if run_match:
        return {'tool': 'RUN_COMMAND', 'args': {'command': run_match.group(1).strip()}}
        
    # Match [WRITE_FILE: path]
    write_match = re.search(r'\[WRITE_FILE:\s*([^\s\]]+)\]', text)
    if write_match:
        path = write_match.group(1)
        post_text = text[write_match.end():]
        code_block = re.search(r'```(?:\w*)\n([\s\S]*?)```', post_text)
        if code_block:
            content = code_block.group(1)
            return {'tool': 'WRITE_FILE', 'args': {'path': path, 'content': content}}
        else:
            return {'tool': 'WRITE_FILE', 'args': {'path': path, 'content': post_text.strip()}}
            
    return None

def execute_agent_tool(tool_name, args, project_path):
    if tool_name == 'READ_FILE':
        path = args.get('path', '').strip()
        if path.startswith('./'):
            path = path[2:]
        if '..' in path or path.startswith('/'):
            return "Error: Invalid path. Path must be relative to project root and cannot contain '..'"
        filepath = os.path.join(project_path, path)
        if not os.path.exists(filepath):
            return f"Error: File not found: {path}"
        if os.path.isdir(filepath):
            return f"Error: {path} is a directory. Use LIST_DIR instead."
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return f"--- Content of {path} ---\n{content}\n----------------"
        except Exception as e:
            return f"Error reading file: {str(e)}"

    elif tool_name == 'WRITE_FILE':
        path = args.get('path', '').strip()
        content = args.get('content', '')
        if path.startswith('./'):
            path = path[2:]
        if '..' in path or path.startswith('/'):
            return "Error: Invalid path. Path must be relative to project root and cannot contain '..'"
        filepath = os.path.join(project_path, path)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Success: File written successfully to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    elif tool_name == 'LIST_DIR':
        path = args.get('path', '').strip()
        if path.startswith('./'):
            path = path[2:]
        if '..' in path or path.startswith('/'):
            return "Error: Invalid path"
        target_path = os.path.join(project_path, path) if path and path != '.' else project_path
        if not os.path.exists(target_path):
            return f"Error: Directory not found: {path}"
        try:
            entries = []
            for entry in os.scandir(target_path):
                if entry.name in EXCLUDE_DIRS or entry.name in EXCLUDE_FILES:
                    continue
                rel = os.path.relpath(entry.path, project_path)
                entries.append(f"{'[DIR]' if entry.is_dir() else '[FILE]'} {rel}")
            return "\n".join(sorted(entries)) if entries else "Empty directory"
        except Exception as e:
            return f"Error listing directory: {str(e)}"

    elif tool_name == 'SEARCH_FILES':
        query = args.get('query', '').strip()
        if not query:
            return "Error: Empty search query"
        results = []
        query_lower = query.lower()
        try:
            for root, dirs, files in os.walk(project_path):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for f in files:
                    if f in EXCLUDE_FILES:
                        continue
                    rel_path = os.path.relpath(os.path.join(root, f), project_path)
                    if query_lower in rel_path.lower():
                        results.append(f"Match in filename: {rel_path}")
                    filepath = os.path.join(root, f)
                    if os.path.getsize(filepath) > 500000: # Skip files larger than 500KB to prevent memory hangs
                        continue
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as file_obj:
                            content = file_obj.read()
                            if query_lower in content.lower():
                                lines = content.split('\n')
                                for idx, line in enumerate(lines):
                                    if query_lower in line.lower():
                                        results.append(f"{rel_path}:{idx+1}: {line.strip()[:120]}")
                    except:
                        pass
            return "\n".join(results[:50]) if results else "No matches found"
        except Exception as e:
            return f"Error searching files: {str(e)}"

    elif tool_name == 'RUN_COMMAND':
        command = args.get('command', '').strip()
        if not command:
            return "Error: Empty command"
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = f"Exit code: {res.returncode}\n"
            if res.stdout:
                output += f"STDOUT:\n{res.stdout}\n"
            if res.stderr:
                output += f"STDERR:\n{res.stderr}\n"
            return output
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds."
        except Exception as e:
            return f"Error executing command: {str(e)}"

    return f"Error: Unknown tool {tool_name}"

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
    tree_nodes, _ = scan_directory_and_stats(project_path, project_path, max_depth=config.AGENT_MAX_DEPTH)
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
