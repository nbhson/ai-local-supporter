import os
import base64
import logging
from celery_app import celery
from services.document_service import (
    extract_text_from_file, extract_text_from_image_ocr,
    is_image_file, resize_and_compress_image
)
from services.rag_service import index_document

logging.basicConfig(level=logging.INFO)

@celery.task(name="tasks.process_document_task")
def process_document_task(session_id, filepath, language, model):
    """Asynchronously process document: extract text/image, run OCR, chunk and embed into ChromaDB."""
    # Local imports to prevent circular imports during app initialization
    from app import app, db
    from services.models import DocumentSession, ChatMessage
    from services.ollama_service import is_vision_model
    
    with app.app_context():
        try:
            logging.info(f"Starting background processing for session {session_id}, file={filepath}")
            session = DocumentSession.query.get(session_id)
            if not session:
                logging.error(f"Session {session_id} not found in database.")
                return
                
            filename = session.filename
            is_image = is_image_file(filepath)
            
            extracted_text = ""
            base64_image = None
            
            if is_image:
                # Process image
                base64_image = resize_and_compress_image(filepath)
                if not base64_image:
                    with open(filepath, 'rb') as img_file:
                        base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                
                # Check if model supports vision
                if not is_vision_model(model):
                    logging.info(f"Model {model} is not a vision model. Falling back to OCR.")
                    ocr_text = extract_text_from_image_ocr(filepath)
                    if ocr_text:
                        if ocr_text.startswith("OCR Error"):
                            raise Exception(ocr_text)
                        extracted_text = ocr_text
                    else:
                        logging.info("OCR returned empty text. Using fallback placeholder.")
                        extracted_text = "[Không tìm thấy văn bản nào trong hình ảnh / No text detected in this image]"
                else:
                    extracted_text = "[Image analyzed via vision model]"
            else:
                # Process text document (PDF, DOCX, TXT, etc.)
                extracted_text = extract_text_from_file(filepath)
                if extracted_text is None or extracted_text.startswith("Error"):
                    raise Exception(extracted_text or "Text extraction failed.")
            
            # Index document content into Vector DB for RAG if it has text context
            if extracted_text and extracted_text != "[Image analyzed via vision model]":
                num_chunks = index_document(session_id, extracted_text)
                logging.info(f"Successfully chunked and indexed {num_chunks} chunks for session {session_id}")
            
            # Formulate greeting
            if is_image and base64_image and extracted_text == "[Image analyzed via vision model]":
                greeting = f"Tôi đã nhận diện hình ảnh \"{filename}\". Bạn cần tôi trợ giúp gì về hình ảnh này?" if language == 'vi' else f"I have processed the image \"{filename}\". How can I help you with it?"
            else:
                greeting = f"Tôi đã phân tích xong tài liệu \"{filename}\". Bạn cần tôi giúp gì về nội dung này?" if language == 'vi' else f"I have analyzed the document \"{filename}\". How can I help you with it?"
            
            # Update database record
            session.status = 'ready'
            session.base64_image = base64_image
            session.extracted_text = extracted_text
            db.session.add(session)
            
            # Add greeting message to chat history
            greeting_msg = ChatMessage(session_id=session_id, role='assistant', content=greeting)
            db.session.add(greeting_msg)
            
            db.session.commit()
            logging.info(f"Session {session_id} is ready.")
            
        except Exception as e:
            logging.exception(f"Error occurred in process_document_task: {e}")
            session = DocumentSession.query.get(session_id)
            if session:
                session.status = 'failed'
                session.error_message = str(e)
                db.session.add(session)
                db.session.commit()
