import os
import re
import time
import json
import logging
import subprocess
import config
from services.database import db
from services.models import ChatMessage
from services.ollama_service import call_ollama
from services.helper_service import get_lang_instruction, format_sse_event, retrieve_chat_history, save_chat_message

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
                if entry.name in config.EXCLUDE_DIRS:
                    continue
                subtree, _ = scan_directory_and_stats(entry.path, base_path, stats, current_depth + 1, max_depth)
                tree.append({
                    "name": entry.name,
                    "path": os.path.relpath(entry.path, base_path),
                    "is_dir": True,
                    "children": subtree
                })
            else:
                if entry.name in config.EXCLUDE_FILES:
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
    if '[FINISH]' in text:
        return {'tool': 'FINISH', 'args': {}}
        
    read_match = re.search(r'\[READ_FILE:\s*([^\s\]]+)\]', text)
    if read_match:
        return {'tool': 'READ_FILE', 'args': {'path': read_match.group(1)}}
        
    list_match = re.search(r'\[LIST_DIR:\s*([^\s\]]+)\]', text)
    if list_match:
        return {'tool': 'LIST_DIR', 'args': {'path': list_match.group(1)}}
        
    search_match = re.search(r'\[SEARCH_FILES:\s*([^\]]+)\]', text)
    if search_match:
        return {'tool': 'SEARCH_FILES', 'args': {'query': search_match.group(1).strip()}}
        
    run_match = re.search(r'\[RUN_COMMAND:\s*([^\]]+)\]', text)
    if run_match:
        return {'tool': 'RUN_COMMAND', 'args': {'command': run_match.group(1).strip()}}
        
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

from services.agent_tool_service import ToolRegistry

def execute_agent_tool(tool_name, args, project_path):
    return ToolRegistry.execute_tool(tool_name, args, project_path)

def generate_agent_stream(session_id, project_path, question, language, model, context_str, tree_str, agent_mode):
    """Executes the main ReAct software development agent loop, yielding SSE events."""
    from app import app
    with app.app_context():
        lang_instruction = get_lang_instruction(language)
        
        if agent_mode:
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
        else:
            system_prompt = f"""You are a helpful software engineering assistant helping the user work on a local project workspace.
{lang_instruction}

CURRENT DIRECTORY TREE STRUCTURE:
```
{tree_str}
```
{context_str}

Answer the user's questions about the project files directly, explain code, or answer general queries.
Since you are in direct chat mode, do NOT use any tool call tags such as [READ_FILE], [WRITE_FILE], [LIST_DIR], [SEARCH_FILES], [RUN_COMMAND], or [FINISH].
Provide clear, well-structured explanations and code suggestions where appropriate.
For thought process, keep it extremely concise (1-2 sentences) inside <think>...</think>. For simple greetings or casual chat, SKIP the thought process and reply immediately.
"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Retrieve history
        messages.extend(retrieve_chat_history(session_id, config.PROJECT_HISTORY_LIMIT, skip_first=False))
        
        # Save user message to history
        save_chat_message(session_id, 'user', question)
        
        # Append current user question
        messages.append({"role": "user", "content": question})
        
        max_iterations = config.AGENT_MAX_ITERATIONS if agent_mode else 1
        initial_messages_count = len(messages)

        for iteration in range(max_iterations):
            # Send iteration status
            status_msg = f"AI is thinking (Loop {iteration+1}/10)..." if language == 'en' else f"AI đang suy nghĩ (Vòng lặp {iteration+1}/10)..."
            yield format_sse_event('agent_status', status=status_msg)
            time.sleep(0.1)
            
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
                                yield format_sse_event('content', content=content)
                            elif "error" in data_json:
                                error_msg = data_json["error"]
                                yield format_sse_event('content', content=f"❌ **Error:** {error_msg}")
                        except:
                            pass
            
            # Append assistant response to messages history
            messages.append({"role": "assistant", "content": current_answer})
            
            # Parse tool call
            tool_call = parse_tool_call(current_answer)
            if not tool_call:
                yield format_sse_event('agent_status', status='Finished (No tool call)' if language == 'en' else 'Hoàn thành (Không có tool call)')
                break
                
            tool_name = tool_call['tool']
            tool_args = tool_call['args']
            
            # Yield tool call event
            yield format_sse_event('tool_call', tool=tool_name, args=tool_args)
            
            tool_status = f"Running tool {tool_name}..." if language == 'en' else f"Đang chạy tool {tool_name}..."
            if tool_name == 'READ_FILE':
                tool_status = f"Reading file: {tool_args.get('path')}..." if language == 'en' else f"Đang đọc file: {tool_args.get('path')}..."
            elif tool_name == 'WRITE_FILE':
                tool_status = f"Writing file: {tool_args.get('path')}..." if language == 'en' else f"Đang ghi file: {tool_args.get('path')}..."
            elif tool_name == 'RUN_COMMAND':
                tool_status = f"Running command: {tool_args.get('command')}..." if language == 'en' else f"Đang chạy lệnh: {tool_args.get('command')}..."
            yield format_sse_event('agent_status', status=tool_status)
            time.sleep(0.1)
            
            if tool_name == 'FINISH':
                yield format_sse_event('agent_status', status='Agent finished tasks successfully!' if language == 'en' else 'Agent hoàn thành công việc thành công!')
                break
            
            # Execute tool
            tool_result = execute_agent_tool(tool_name, tool_args, project_path)
            
            # Yield tool result event
            display_result = tool_result
            if len(display_result) > 5000:
                display_result = display_result[:5000] + "\n...[output truncated due to length]"
            yield format_sse_event('tool_result', tool=tool_name, args=tool_args, result=display_result)
            
            post_status = f"Finished. AI is analyzing results..." if language == 'en' else f"Đã chạy xong tool. AI đang phân tích kết quả..."
            if tool_name == 'READ_FILE':
                post_status = f"Read finished. AI is analyzing file..." if language == 'en' else f"Đã đọc file xong. AI đang phân tích..."
            elif tool_name == 'WRITE_FILE':
                post_status = f"Write finished. AI is validating..." if language == 'en' else f"Đã ghi file xong. AI đang kiểm tra..."
            elif tool_name == 'RUN_COMMAND':
                post_status = f"Command finished. AI is analyzing output..." if language == 'en' else f"Đã chạy lệnh xong. AI đang phân tích kết quả..."
            yield format_sse_event('agent_status', status=post_status)
            time.sleep(0.1)
            
            # Append result to messages history for next turn
            model_tool_result = tool_result
            if len(model_tool_result) > 15000:
                model_tool_result = model_tool_result[:15000] + "\n\n...[content truncated to save context]..."
            
            messages.append({
                "role": "user",
                "content": f"Tool execution result for [{tool_name}]:\n{model_tool_result}\n\nPlease proceed to the next step."
            })
        
        # Save final response summary to SQLite
        final_summary = ""
        for msg in messages[initial_messages_count:]:
            if msg["role"] == "assistant":
                final_summary += msg["content"] + "\n\n"
        
        save_chat_message(session_id, 'assistant', final_summary.strip())
        
        yield "data: [DONE]\n\n"
