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

# In-memory cache for project tree
# Format: session_id -> {"tree": tree, "stats": stats, "timestamp": float}
_project_tree_cache = {}

def get_cached_project_tree(session_id):
    """Retrieve the cached project tree and stats for a session."""
    cache_entry = _project_tree_cache.get(session_id)
    if cache_entry:
        return cache_entry["tree"], cache_entry["stats"]
    return None, None

def set_cached_project_tree(session_id, tree, stats):
    """Cache the project tree and stats for a session."""
    _project_tree_cache[session_id] = {
        "tree": tree,
        "stats": stats,
        "timestamp": time.time()
    }

def invalidate_project_tree_cache(session_id):
    """Invalidate/delete the cached project tree for a session."""
    if session_id in _project_tree_cache:
        del _project_tree_cache[session_id]

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

def parse_all_tool_calls(text):
    """
    Parses all tool calls from the assistant response text.
    Returns a list of dicts: [{'tool': tool_name, 'args': tool_args}]
    """
    if '[FINISH]' in text:
        return [{'tool': 'FINISH', 'args': {}}]
        
    tool_calls = []
    
    # Match tool tags: [READ_FILE: ...], [LIST_DIR: ...], [SEARCH_FILES: ...], [RUN_COMMAND: ...], [WRITE_FILE: ...]
    pattern = r'\[(READ_FILE|WRITE_FILE|LIST_DIR|SEARCH_FILES|RUN_COMMAND):\s*([^\]\n]+)\]'
    matches = list(re.finditer(pattern, text))
    
    for idx, match in enumerate(matches):
        tool_name = match.group(1)
        arg_val = match.group(2).strip()
        
        if tool_name == 'READ_FILE':
            tool_calls.append({'tool': 'READ_FILE', 'args': {'path': arg_val}})
        elif tool_name == 'LIST_DIR':
            tool_calls.append({'tool': 'LIST_DIR', 'args': {'path': arg_val}})
        elif tool_name == 'SEARCH_FILES':
            tool_calls.append({'tool': 'SEARCH_FILES', 'args': {'query': arg_val}})
        elif tool_name == 'RUN_COMMAND':
            tool_calls.append({'tool': 'RUN_COMMAND', 'args': {'command': arg_val}})
        elif tool_name == 'WRITE_FILE':
            # Extract content between this WRITE_FILE tag and the next tool call tag, or end of text.
            start_pos = match.end()
            end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            segment = text[start_pos:end_pos]
            
            # Extract code block if present
            code_block = re.search(r'```(?:\w*)\n([\s\S]*?)```', segment)
            if code_block:
                content = code_block.group(1)
            else:
                content = segment.strip()
            tool_calls.append({'tool': 'WRITE_FILE', 'args': {'path': arg_val, 'content': content}})
            
    return tool_calls

def parse_tool_call(text):
    """Legacy parser for compatibility with tests."""
    calls = parse_all_tool_calls(text)
    return calls[0] if calls else None

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
4. You can call multiple tools at the end of your response in parallel if you need to gather information or make changes to multiple files (e.g. read multiple files or write multiple files). Output all tool calls you want to execute in this turn together.
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
- You can output multiple tool call tags at the end of your response when you need info or actions on multiple files.
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
            
            # Parse tool calls
            tool_calls = parse_all_tool_calls(current_answer)
            if not tool_calls:
                yield format_sse_event('agent_status', status='Finished (No tool call)' if language == 'en' else 'Hoàn thành (Không có tool call)')
                break
                
            # Check for FINISH
            has_finish = any(tc['tool'] == 'FINISH' for tc in tool_calls)
            if has_finish:
                yield format_sse_event('agent_status', status='Agent finished tasks successfully!' if language == 'en' else 'Agent hoàn thành công việc thành công!')
                break
            
            results_contents = []
            for idx, tool_call in enumerate(tool_calls):
                tool_name = tool_call['tool']
                tool_args = tool_call['args']
                call_id = f"call_{iteration}_{idx}"
                
                # Yield tool call event
                yield format_sse_event('tool_call', tool=tool_name, args=tool_args, call_id=call_id)
                
                tool_status = f"Running tool {tool_name}..." if language == 'en' else f"Đang chạy tool {tool_name}..."
                if tool_name == 'READ_FILE':
                    tool_status = f"Reading file: {tool_args.get('path')}..." if language == 'en' else f"Đang đọc file: {tool_args.get('path')}..."
                elif tool_name == 'WRITE_FILE':
                    tool_status = f"Writing file: {tool_args.get('path')}..." if language == 'en' else f"Đang ghi file: {tool_args.get('path')}..."
                elif tool_name == 'RUN_COMMAND':
                    tool_status = f"Running command: {tool_args.get('command')}..." if language == 'en' else f"Đang chạy lệnh: {tool_args.get('command')}..."
                yield format_sse_event('agent_status', status=tool_status)
                time.sleep(0.05)
                
                # Execute tool
                tool_result = execute_agent_tool(tool_name, tool_args, project_path)
                if tool_name == 'WRITE_FILE':
                    invalidate_project_tree_cache(session_id)
                
                # Yield tool result event
                display_result = tool_result
                if len(display_result) > 5000:
                    display_result = display_result[:5000] + "\n...[output truncated due to length]"
                yield format_sse_event('tool_result', tool=tool_name, args=tool_args, result=display_result, call_id=call_id)
                
                post_status = f"Finished tool {tool_name}." if language == 'en' else f"Đã chạy xong tool {tool_name}."
                yield format_sse_event('agent_status', status=post_status)
                time.sleep(0.05)
                
                # Format output for model prompt
                model_tool_result = tool_result
                if len(model_tool_result) > 15000:
                    model_tool_result = model_tool_result[:15000] + "\n\n...[content truncated to save context]..."
                results_contents.append(f"Tool execution result for [{tool_name}] with args {json.dumps(tool_args)}:\n{model_tool_result}")
            
            # Combine all results into one user message for the next iteration
            combined_results = "\n\n---\n\n".join(results_contents)
            messages.append({
                "role": "user",
                "content": f"Tool execution results:\n\n{combined_results}\n\nPlease proceed to the next step."
            })
        
        # Save final response summary to SQLite
        final_summary = ""
        for msg in messages[initial_messages_count:]:
            if msg["role"] == "assistant":
                final_summary += msg["content"] + "\n\n"
        
        save_chat_message(session_id, 'assistant', final_summary.strip())
        
        yield "data: [DONE]\n\n"
