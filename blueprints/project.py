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
from services.models import ProjectSession, ChatMessage
from services.ollama_service import call_ollama

project_bp = Blueprint('project', __name__)

EXCLUDE_DIRS = {
    '.git', 'node_modules', '.venv', 'venv', 'env', '.idea', '__pycache__', 
    'dist', 'build', 'target', '.npm', '.cache', '.angular', '.next', '.nuxt',
    '.sass-cache', '.svelte-kit', '.agents', '.gemini', 'coverage', '.nyc_output'
}
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

def scan_directory(current_path, base_path, current_depth=0, max_depth=None):
    tree = []
    if max_depth is not None and current_depth > max_depth:
        return tree
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
                    "children": scan_directory(entry.path, base_path, current_depth + 1, max_depth)
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

def get_simple_tree_str(nodes, depth=0, max_depth=2, max_entries_per_dir=30):
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
    session = ProjectSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    project_path = session.project_path
    data = request.json or {}
    question = data.get('question', '').strip()
    language = data.get('language', 'en')
    model = data.get('model', session.model or config.DEFAULT_MODEL)
    context_files = data.get('context_files', [])
    
    if not question:
        return jsonify({"error": "Question is empty"}), 400
        
    lang_instruction = "Respond in English." if language == "en" else "Hãy phản hồi bằng Tiếng Việt."
    
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
                    # Truncate large files to save context window (keep first 8000 characters)
                    if len(content) > 8000:
                        content = content[:8000] + "\n\n...[content truncated to save context]..."
                    context_str_parts.append(f"\nFile: `{rel_path}`\n```\n{content}\n```")
                except Exception as e:
                    context_str_parts.append(f"\nFile: `{rel_path}` (Error reading content: {str(e)})")
        context_str = "\n".join(context_str_parts)

    # Get initial project tree (limit depth to 2 for context)
    tree_nodes = scan_directory(project_path, project_path, max_depth=2)
    tree_str = "\n".join(get_simple_tree_str(tree_nodes))
    
    system_prompt = f"""You are a professional AI Software Engineering Agent helping the user work on a local project workspace.
You have direct read/write access to the files and can execute terminal commands within this directory.
{lang_instruction}

CURRENT DIRECTORY TREE STRUCTURE:
```
{tree_str}
```
{context_str}

YOUR WORKFLOW:
1. Understand the user's request.
2. Outline your plan of actions in your thought process.
3. Perform actions step-by-step using the following TOOL CALLS.
4. ONLY call ONE tool at a time in a single turn. After a tool call tag, STOP generating text and wait for the tool output from the system.
5. Once you have finished all tasks and verified them, output [FINISH] with a final explanation of the changes.

TOOL CALL SYNTAX:
To call a tool, you MUST output the exact tag format at the very end of your response:

- Read a file's content:
  [READ_FILE: path/to/file.ext]
- Write/overwrite a file:
  [WRITE_FILE: path/to/file.ext]
  ```language
  // full code content
  ```
- List directory contents:
  [LIST_DIR: path/to/dir] (use "." for root)
- Search for keyword in filenames or contents:
  [SEARCH_FILES: keyword]
- Run a terminal command (e.g. run test, compile, lint, syntax check):
  [RUN_COMMAND: command]
- Mark the task as fully completed:
  [FINISH]

RULES:
- When writing files, ALWAYS output the FULL file content in code block.
- Paths must be relative to the project root (no leading '/').
- Do not output multiple tool calls in one turn. Output exactly ONE tool call tag at the end of your response when you need info or action.
- For thought process, keep it extremely concise (1-2 sentences) inside <think>...</think>. For simple greetings or casual chat, SKIP the thought process and reply immediately.
- CRITICAL: You must ONLY read files that actually exist in the project. Check the "CURRENT DIRECTORY TREE STRUCTURE" list above to verify if a file exists before trying to read it. Do NOT guess, assume, or hallucinate file paths (e.g. project-overview.md, frontend-architecture.md, etc.) if they are not listed in the tree.
- CRITICAL: If a file's content is already provided in the ADDITIONAL CONTEXT, DO NOT use [READ_FILE] on it and DO NOT print its code in your response. Answer the user directly!
- If the user is only asking a question, explanation, or general query that does NOT require modifying files or running commands, answer the query directly and append [FINISH] at the end of your response. Do NOT call other tools like [READ_FILE] or [LIST_DIR] unnecessarily.
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Retrieve chat history (max 8 messages)
    chat_history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()
    for msg in chat_history[-8:]:
        content = msg.content
        if len(content) > 3000:
            content = content[:3000] + "\n\n...[content truncated in history to save context]..."
        messages.append({"role": msg.role, "content": content})
        
    # Save user message to history
    user_msg = ChatMessage(session_id=session_id, role='user', content=question)
    db.session.add(user_msg)
    db.session.commit()
    
    # Append user question
    messages.append({"role": "user", "content": question})
    
    def generate():
        from app import app
        with app.app_context():
            max_iterations = 10
            initial_messages_count = len(messages)

            
            def make_sse(event_type, **kwargs):
                payload = json.dumps({'type': event_type, **kwargs})
                padding = ":" + " " * 1024 + "\n"
                return f"data: {payload}\n\n{padding}"
            
            for iteration in range(max_iterations):
                # Send iteration status
                status_msg = f"AI is thinking (Loop {iteration+1}/10)..." if language == 'en' else f"AI đang suy nghĩ (Vòng lặp {iteration+1}/10)..."
                yield make_sse('agent_status', status=status_msg)
                time.sleep(0.1) # Give OS a moment to flush the socket
                
                # Call Ollama
                current_answer = ""
                generator = call_ollama(messages, model, stream=True)
                
                for chunk in generator:
                    if chunk.startswith("data: "):
                        data_str = chunk[6:].strip()
                        if data_str != "[DONE]":
                            try:
                                data_json = json.loads(data_str)
                                if "content" in data_json:
                                    content = data_json["content"]
                                    current_answer += content
                                    yield make_sse('content', content=content)
                                elif "error" in data_json:
                                    error_msg = data_json["error"]
                                    yield make_sse('content', content=f"❌ **Error:** {error_msg}")
                            except:
                                pass
                
                # Append assistant response to messages history
                messages.append({"role": "assistant", "content": current_answer})
                
                # Parse tool call
                tool_call = parse_tool_call(current_answer)
                if not tool_call:
                    # Finish loop if no tool call is output
                    yield make_sse('agent_status', status='Finished (No tool call)' if language == 'en' else 'Hoàn thành (Không có tool call)')
                    break
                    
                tool_name = tool_call['tool']
                tool_args = tool_call['args']
                
                # Yield tool call event
                yield make_sse('tool_call', tool=tool_name, args=tool_args)
                
                tool_status = f"Running tool {tool_name}..." if language == 'en' else f"Đang chạy tool {tool_name}..."
                if tool_name == 'READ_FILE':
                    tool_status = f"Reading file: {tool_args.get('path')}..." if language == 'en' else f"Đang đọc file: {tool_args.get('path')}..."
                elif tool_name == 'WRITE_FILE':
                    tool_status = f"Writing file: {tool_args.get('path')}..." if language == 'en' else f"Đang ghi file: {tool_args.get('path')}..."
                elif tool_name == 'RUN_COMMAND':
                    tool_status = f"Running command: {tool_args.get('command')}..." if language == 'en' else f"Đang chạy lệnh: {tool_args.get('command')}..."
                yield make_sse('agent_status', status=tool_status)
                time.sleep(0.1) # Give OS a moment to flush the socket
                
                if tool_name == 'FINISH':
                    yield make_sse('agent_status', status='Agent finished tasks successfully!' if language == 'en' else 'Agent hoàn thành công việc thành công!')
                    break
                
                # Execute tool
                tool_result = execute_agent_tool(tool_name, tool_args, project_path)
                
                # Yield tool result event
                # Keep output safe, limit size sent over SSE
                display_result = tool_result
                if len(display_result) > 5000:
                    display_result = display_result[:5000] + "\n...[output truncated due to length]"
                yield make_sse('tool_result', tool=tool_name, args=tool_args, result=display_result)
                
                post_status = f"Finished. AI is analyzing results..." if language == 'en' else f"Đã chạy xong tool. AI đang phân tích kết quả..."
                if tool_name == 'READ_FILE':
                    post_status = f"Read finished. AI is analyzing file..." if language == 'en' else f"Đã đọc file xong. AI đang phân tích..."
                elif tool_name == 'WRITE_FILE':
                    post_status = f"Write finished. AI is validating..." if language == 'en' else f"Đã ghi file xong. AI đang kiểm tra..."
                elif tool_name == 'RUN_COMMAND':
                    post_status = f"Command finished. AI is analyzing output..." if language == 'en' else f"Đã chạy lệnh xong. AI đang phân tích kết quả..."
                yield make_sse('agent_status', status=post_status)
                time.sleep(0.1) # Give OS a moment to flush the socket
                
                # Append result to messages history for next turn
                # Truncate content to save context and speed up Ollama prompt evaluation
                model_tool_result = tool_result
                if len(model_tool_result) > 8000:
                    model_tool_result = model_tool_result[:8000] + "\n\n...[content truncated to save context]..."
                
                messages.append({
                    "role": "user",
                    "content": f"Tool execution result for [{tool_name}]:\n{model_tool_result}\n\nPlease proceed to the next step."
                })
            
            # Save final response summary to SQLite
            final_summary = ""
            for msg in messages[initial_messages_count:]:
                if msg["role"] == "assistant":
                    final_summary += msg["content"] + "\n\n"
            
            assistant_msg = ChatMessage(session_id=session_id, role='assistant', content=final_summary.strip())
            db.session.add(assistant_msg)
            db.session.commit()
            
            yield "data: [DONE]\n\n"
            
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response
