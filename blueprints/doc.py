import os
import uuid
import base64
import logging
import threading
import json
from flask import Blueprint, request, jsonify, Response, current_app
from werkzeug.utils import secure_filename

import config
from services.session_store import doc_sessions
from services.document_service import (
    allowed_file, is_image_file, extract_text_from_file,
    extract_text_from_image_ocr, resize_and_compress_image,
    cleanup_old_uploads
)
from services.ollama_service import (
    is_vision_model, call_ollama, analyze_with_ollama
)

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
    extracted_text = extract_text_from_file(filepath)

    # Determine language instruction
    lang_instruction = "Respond in English." if language == "en" else "Respond in Vietnamese."

    # For images, check if model supports vision
    if is_image:
        base64_image = resize_and_compress_image(filepath)
        if not base64_image:
            with open(filepath, 'rb') as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Get the correct MIME type based on file extension
        ext = filepath.rsplit('.', 1)[1].lower() if '.' in filepath else 'jpeg'
        mime_type_map = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'tif': 'image/tiff',
            'webp': 'image/webp'
        }
        mime_type = mime_type_map.get(ext, 'image/jpeg')
        logging.info(f"Image upload: filename={filename}, model={model}, is_vision={is_vision_model(model)}, mime_type={mime_type}")
        
        # Check if the selected model is actually a vision model
        if not is_vision_model(model):
            logging.warning(f"Model {model} is not a vision model. Falling back to OCR.")
            # Fallback to OCR for non-vision models
            ocr_text = extract_text_from_image_ocr(filepath)
            if ocr_text and not ocr_text.startswith("OCR Error"):
                # Truncate to safe length (15k chars)
                max_chars = 15000
                if len(ocr_text) > max_chars:
                    ocr_text = ocr_text[:max_chars] + "\n\n...[truncated]"

                session_id = uuid.uuid4().hex
                greeting = f"Tôi đã phân tích xong tài liệu \"{filename}\". Bạn cần tôi giúp gì về nội dung này?" if language == 'vi' else f"I have analyzed the document \"{filename}\". How can I help you with it?"
                
                doc_sessions[session_id] = {
                    "filename": filename, 
                    "filepath": filepath, 
                    "text": ocr_text,
                    "model": model, 
                    "file_type": "document", 
                    "conversation": [
                        {"role": "assistant", "content": greeting}
                    ],
                    "language": language
                }
                
                return jsonify({
                    "session_id": session_id, 
                    "filename": filename, 
                    "file_type": "document",
                    "greeting": greeting,
                    "text_preview": ocr_text[:500]
                })
            else:
                return jsonify({
                    "error": f"Model {model} không hỗ trợ đọc ảnh. Hãy dùng qwen2.5-vl:7b hoặc OCR fallback thất bại: {ocr_text}"
                }), 400

        # Use vision model directly
        session_id = uuid.uuid4().hex
        greeting = f"Tôi đã nhận diện hình ảnh \"{filename}\". Bạn cần tôi trợ giúp gì về hình ảnh này?" if language == 'vi' else f"I have processed the image \"{filename}\". How can I help you with it?"
        
        doc_sessions[session_id] = {
            "filename": filename, 
            "filepath": filepath, 
            "text": "[Image analyzed via vision model]",
            "model": model, 
            "file_type": "image", 
            "conversation": [
                {"role": "assistant", "content": greeting}
            ],
            "base64_image": base64_image,
            "language": language
        }
        
        return jsonify({
            "session_id": session_id, 
            "filename": filename, 
            "file_type": "image",
            "greeting": greeting,
            "text_preview": ""
        })

    # Text-based files
    if extracted_text is None or extracted_text.startswith("Error"):
        os.remove(filepath)
        return jsonify({"error": extracted_text or "Could not extract text"}), 400

    # Truncate to safe length (15k chars)
    max_chars = 15000
    if len(extracted_text) > max_chars:
        extracted_text = extracted_text[:max_chars] + "\n\n...[truncated]"

    session_id = uuid.uuid4().hex
    greeting = f"Tôi đã phân tích xong tài liệu \"{filename}\". Bạn cần tôi giúp gì về nội dung này?" if language == 'vi' else f"I have analyzed the document \"{filename}\". How can I help you with it?"
    
    doc_sessions[session_id] = {
        "filename": filename, 
        "filepath": filepath, 
        "text": extracted_text,
        "model": model, 
        "file_type": "document", 
        "conversation": [
            {"role": "assistant", "content": greeting}
        ],
        "language": language
    }

    return jsonify({
        "session_id": session_id, 
        "filename": filename, 
        "file_type": "document",
        "greeting": greeting,
        "text_preview": extracted_text[:500]
    })

@doc_bp.route('/chat', methods=['POST'])
def chat_document():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data"}), 400
    session_id = data.get('session_id')
    question = data.get('question', '').strip()
    language = data.get('language', 'en')
    if not session_id or session_id not in doc_sessions:
        return jsonify({"error": "Session not found. Upload a file first."}), 400
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    session = doc_sessions[session_id]
    model = data.get('model', session.get('model', config.DEFAULT_MODEL))
    is_image = session.get('file_type') == 'image'

    # Determine language instruction
    lang_instruction = "Respond in English." if language == "en" else "Respond in Vietnamese."

    if is_image and session.get('base64_image'):
        # Send image + question to vision model
        messages = []
        for msg in session["conversation"][-10:]:
            messages.append(msg)
        messages.append({
            "role": "user",
            "content": f"{question}\n\n{lang_instruction}",
            "images": [session['base64_image']]
        })
    else:
        system_prompt = f"""You are a document analysis assistant. Answer based ONLY on the document.
Document: {session['filename']}
Content: {session['text']}
{lang_instruction}"""
        messages = [{"role": "system", "content": system_prompt}]
        for msg in session["conversation"][-10:]:
            messages.append(msg)
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

@doc_bp.route('/session/<session_id>/clear', methods=['POST'])
def clear_doc_session(session_id):
    if session_id not in doc_sessions:
        return jsonify({"error": "Session not found"}), 404
    # Reset conversation history but keep initial analysis block
    if len(doc_sessions[session_id]["conversation"]) >= 1:
        initial_setup = doc_sessions[session_id]["conversation"][:1]
        doc_sessions[session_id]["conversation"] = initial_setup
    else:
        doc_sessions[session_id]["conversation"] = []
    return jsonify({"success": True})
