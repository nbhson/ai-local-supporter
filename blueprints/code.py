import uuid
import json
from flask import Blueprint, request, jsonify, Response

import config
from services.session_store import code_sessions
from services.ollama_service import call_ollama, analyze_with_ollama

code_bp = Blueprint('code', __name__)

@code_bp.route('/analyze', methods=['POST'])
def analyze_code():
    data = request.json
    if not data or 'code' not in data:
        return jsonify({"error": "No code provided"}), 400

    code = data['code'].strip()
    if not code:
        return jsonify({"error": "Code cannot be empty"}), 400

    # Truncate to safe length (15k chars)
    max_chars = 15000
    if len(code) > max_chars:
        code = code[:max_chars] + "\n\n...[truncated]"

    language = data.get('language', 'auto-detect')
    model = data.get('model', config.DEFAULT_MODEL)
    ui_language = data.get('ui_language', 'en')  # Get UI language from frontend

    # Create the greeting message
    if ui_language == 'vi':
        greeting = "Tôi đã nhận đoạn code của bạn. Bạn muốn tôi giải thích, tìm lỗi hay tối ưu đoạn code này?"
    else:
        greeting = "I have received your code. Would you like me to explain, debug, or optimize it?"

    session_id = uuid.uuid4().hex

    code_sessions[session_id] = {
        "code": code,
        "language": language,
        "model": model,
        "conversation": [
            {"role": "assistant", "content": greeting}
        ],
        "ui_language": ui_language
    }

    return jsonify({
        "session_id": session_id,
        "language": language,
        "code_preview": code[:500],
        "greeting": greeting
    })

@code_bp.route('/chat', methods=['POST'])
def chat_code():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data"}), 400
    session_id = data.get('session_id')
    question = data.get('question', '').strip()
    language = data.get('language', 'en')
    if not session_id or session_id not in code_sessions:
        return jsonify({"error": "Session not found. Analyze code first."}), 400
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    session = code_sessions[session_id]
    model = data.get('model', session.get('model', config.DEFAULT_MODEL))

    # Determine language instruction
    lang_instruction = "Respond in English." if language == "en" else "Respond in Vietnamese."
    
    system_prompt = f"""You are a code analysis assistant. Answer based on the code provided.
Code language: {session['language']}
Code:
---
{session['code']}
---
{lang_instruction}"""

    messages = [{"role": "system", "content": system_prompt}]
    # Retrieve last 10 messages from history to maintain context
    for msg in session["conversation"][-10:]:
        messages.append(msg)
    
    # Append the new user question
    messages.append({"role": "user", "content": question})

    # Save user message to history
    session["conversation"].append({"role": "user", "content": question})

    def generate():
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
        session["conversation"].append({"role": "assistant", "content": full_answer})

    return Response(generate(), mimetype='text/event-stream')

@code_bp.route('/session/<session_id>/clear', methods=['POST'])
def clear_code_session(session_id):
    if session_id not in code_sessions:
        return jsonify({"error": "Session not found"}), 404
    # Reset conversation history but keep initial setup (first prompt + greeting) to maintain prompt caching
    if len(code_sessions[session_id]["conversation"]) >= 2:
        initial_setup = code_sessions[session_id]["conversation"][:2]
        code_sessions[session_id]["conversation"] = initial_setup
    else:
        code_sessions[session_id]["conversation"] = []
    return jsonify({"success": True})
