import os
import uuid
import base64
import logging
import threading
import json
from flask import Blueprint, request, jsonify, Response, current_app
from werkzeug.utils import secure_filename

import config
from services.database import db
from services.models import DocumentSession, ChatMessage
from services.document_service import (
    allowed_file, is_image_file, cleanup_old_uploads
)
from services.rag_service import retrieve_context
from services.ollama_service import call_ollama
from tasks import process_document_task

doc_bp = Blueprint('doc', __name__)

@doc_bp.route('/upload', methods=['POST'])
def upload_document():
    # Run cleanup in background
    upload_dir = current_app.config['UPLOAD_FOLDER']
    threading.Thread(target=cleanup_old_uploads, args=(upload_dir,), daemon=True).start()
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    model = request.form.get('model', config.DEFAULT_MODEL)
    language = request.form.get('language', 'en')  # Default to English
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not supported"}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(upload_dir, unique_filename)
    file.save(filepath)

    is_image = is_image_file(filepath)
    file_type = "image" if is_image else "document"

    session_id = uuid.uuid4().hex

    # Create DocumentSession in database with status='processing'
    session = DocumentSession(
        session_id=session_id,
        filename=filename,
        filepath=filepath,
        status='processing',
        language=language,
        model=model,
        file_type=file_type
    )
    db.session.add(session)
    db.session.commit()

    # Trigger Celery background task
    process_document_task.delay(session_id, filepath, language, model)

    return jsonify({
        "session_id": session_id,
        "status": "processing",
        "filename": filename
    })

@doc_bp.route('/status/<session_id>', methods=['GET'])
def get_session_status(session_id):
    session = DocumentSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session.status == 'ready':
        # Get greeting message from DB
        greeting_msg = ChatMessage.query.filter_by(session_id=session_id, role='assistant').order_by(ChatMessage.created_at.asc()).first()
        greeting = greeting_msg.content if greeting_msg else ""
        return jsonify({
            "status": "ready",
            "session_id": session_id,
            "filename": session.filename,
            "file_type": session.file_type,
            "greeting": greeting,
            "text_preview": (session.extracted_text or "")[:500]
        })
    elif session.status == 'failed':
        return jsonify({
            "status": "failed",
            "error": session.error_message or "An error occurred during file processing."
        })
    else:
        return jsonify({
            "status": "processing"
        })

@doc_bp.route('/chat', methods=['POST'])
def chat_document():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data"}), 400
    session_id = data.get('session_id')
    question = data.get('question', '').strip()
    language = data.get('language', 'en')
    
    session = DocumentSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found. Upload a file first."}), 400
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    model = data.get('model', session.model or config.DEFAULT_MODEL)
    is_image = session.file_type == 'image'

    # Determine language instruction
    lang_instruction = "Respond in English." if language == "en" else "Respond in Vietnamese."

    if is_image and session.base64_image and session.extracted_text == "[Image analyzed via vision model]":
        # Send image + question to vision model
        messages = []
        # Retrieve last 10 messages from DB
        chat_history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()
        for msg in chat_history[-10:]:
            messages.append({"role": msg.role, "content": msg.content})
            
        messages.append({
            "role": "user",
            "content": f"{question}\n\n{lang_instruction}",
            "images": [session.base64_image]
        })
    else:
        # Perform RAG retrieval for documents or image-with-OCR fallback
        context = retrieve_context(session_id, question, top_k=4)
        
        system_prompt = f"""You are a document analysis assistant. Answer the user question based ONLY on the provided context.
If the answer cannot be found in the context, say "I cannot find the answer in the document."

Context from document:
{context}

{lang_instruction}"""
        messages = [{"role": "system", "content": system_prompt}]
        
        chat_history = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()
        # skip first greeting message in the system prompt context as it's just a welcome message
        for msg in chat_history[1:-10] if len(chat_history) > 10 else chat_history[1:]:
            messages.append({"role": msg.role, "content": msg.content})
            
        messages.append({"role": "user", "content": question})

    # Save user message to database
    user_msg = ChatMessage(session_id=session_id, role='user', content=question)
    db.session.add(user_msg)
    db.session.commit()

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
            
            # Save assistant response to DB
            assistant_msg = ChatMessage(session_id=session_id, role='assistant', content=full_answer)
            db.session.add(assistant_msg)
            db.session.commit()

    return Response(generate(), mimetype='text/event-stream')

@doc_bp.route('/session/<session_id>/clear', methods=['POST'])
def clear_doc_session(session_id):
    session = DocumentSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
        
    # Reset conversation history but keep the first message (greeting)
    first_msg = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).first()
    if first_msg:
        ChatMessage.query.filter(ChatMessage.session_id == session_id, ChatMessage.id != first_msg.id).delete()
    db.session.commit()
    return jsonify({"success": True})
