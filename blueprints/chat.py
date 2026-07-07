import uuid
import json
from flask import Blueprint, request, jsonify, Response

import config
from services.database import db
from services.models import ChatSession, CodeSession, ChatMessage
from services.ollama_service import call_ollama

chat_bp = Blueprint('chat', __name__)

# --- FREE CHAT ENDPOINTS ---

@chat_bp.route('/init', methods=['POST'])
def init_chat():
    data = request.json or {}
    model = data.get('model', config.DEFAULT_MODEL)
    ui_language = data.get('language', 'en')

    session_id = uuid.uuid4().hex

    if ui_language == 'vi':
        greeting = "Xin chào! Tôi là trợ lý AI của bạn. Hôm nay tôi có thể giúp gì cho bạn?"
    else:
        greeting = "Hello! I am your AI assistant. How can I help you today?"

    # Create ChatSession in DB
    session = ChatSession(
        session_id=session_id,
        model=model,
        ui_language=ui_language
    )
    db.session.add(session)

    # Save initial greeting message
    greeting_msg = ChatMessage(
        session_id=session_id,
        role='assistant',
        content=greeting
    )
    db.session.add(greeting_msg)
    db.session.commit()

    return jsonify({
        "session_id": session_id,
        "greeting": greeting
    })

@chat_bp.route('/chat', methods=['POST'])
def chat_free():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data"}), 400
    session_id = data.get('session_id')
    question = data.get('question', '').strip()
    language = data.get('language', 'en')
    
    session = ChatSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found. Initialize chat first."}), 400
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    model = data.get('model', session.model or config.DEFAULT_MODEL)

    # Determine language instruction
    lang_instruction = "Respond in English." if language == "en" else "Respond in Vietnamese."
    
    system_prompt = f"You are a helpful assistant. {lang_instruction}"

    messages = [{"role": "system", "content": system_prompt}]
    
    # Retrieve last 10 messages from DB
    chat_history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()
    for msg in chat_history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Save user message to history
    user_msg = ChatMessage(session_id=session_id, role='user', content=question)
    db.session.add(user_msg)
    db.session.commit()
    
    # Append the new user question to active message context
    messages.append({"role": "user", "content": question})

    def generate():
        # Call Ollama using app context since we access DB inside generate()
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
            
            # Save assistant response to DB
            assistant_msg = ChatMessage(session_id=session_id, role='assistant', content=full_answer)
            db.session.add(assistant_msg)
            db.session.commit()

    return Response(generate(), mimetype='text/event-stream')

@chat_bp.route('/session/<session_id>/clear', methods=['POST'])
def clear_chat_session(session_id):
    session = ChatSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
        
    # Reset conversation history but keep the first message (greeting)
    first_msg = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).first()
    if first_msg:
        ChatMessage.query.filter(ChatMessage.session_id == session_id, ChatMessage.id != first_msg.id).delete()
    db.session.commit()
    return jsonify({"success": True})


# --- CODE CHAT ENDPOINTS ---

@chat_bp.route('/code/analyze', methods=['POST'])
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

    # Create CodeSession in DB
    session = CodeSession(
        session_id=session_id,
        code=code,
        language=language,
        model=model,
        ui_language=ui_language
    )
    db.session.add(session)

    # Save initial greeting message
    greeting_msg = ChatMessage(
        session_id=session_id,
        role='assistant',
        content=greeting
    )
    db.session.add(greeting_msg)
    db.session.commit()

    return jsonify({
        "session_id": session_id,
        "language": language,
        "code_preview": code[:500],
        "greeting": greeting
    })

@chat_bp.route('/code/chat', methods=['POST'])
def chat_code():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data"}), 400
    session_id = data.get('session_id')
    question = data.get('question', '').strip()
    language = data.get('language', 'en')
    
    session = CodeSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found. Analyze code first."}), 400
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    model = data.get('model', session.model or config.DEFAULT_MODEL)

    # Determine language instruction
    lang_instruction = "Respond in English." if language == "en" else "Respond in Vietnamese."
    
    system_prompt = f"""You are a code analysis assistant. Answer based on the code provided.
Code language: {session.language}
Code:
---
{session.code}
---
{lang_instruction}"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Retrieve last 10 messages from DB
    chat_history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()
    for msg in chat_history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Save user message to history
    user_msg = ChatMessage(session_id=session_id, role='user', content=question)
    db.session.add(user_msg)
    db.session.commit()
    
    # Append the new user question to active message context
    messages.append({"role": "user", "content": question})

    def generate():
        # Call Ollama using app context since we access DB inside generate()
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
            
            # Save assistant response to DB
            assistant_msg = ChatMessage(session_id=session_id, role='assistant', content=full_answer)
            db.session.add(assistant_msg)
            db.session.commit()

    return Response(generate(), mimetype='text/event-stream')

@chat_bp.route('/code/session/<session_id>/clear', methods=['POST'])
def clear_code_session(session_id):
    session = CodeSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
        
    # Reset conversation history but keep the first message (greeting)
    first_msg = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).first()
    if first_msg:
        ChatMessage.query.filter(ChatMessage.session_id == session_id, ChatMessage.id != first_msg.id).delete()
    db.session.commit()
    return jsonify({"success": True})
