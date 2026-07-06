import os
import time
import logging
import io
import base64
import PyPDF2
import docx
from PIL import Image
import pytesseract
import config

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

def is_image_file(filepath):
    ext = filepath.rsplit('.', 1)[1].lower() if '.' in filepath else ''
    return ext in config.IMAGE_EXTENSIONS

def extract_text_from_image_ocr(filepath):
    """Extract text from image using Tesseract OCR."""
    try:
        img = Image.open(filepath)
        text = pytesseract.image_to_string(img, lang='vie+eng')
        return text.strip() if text.strip() else None
    except Exception as e:
        return f"OCR Error: {str(e)}"

def extract_text_from_file(filepath):
    ext = filepath.rsplit('.', 1)[1].lower() if '.' in filepath else ''
    try:
        if ext in ('txt', 'md', 'csv', 'json', 'xml', 'yaml', 'yml'):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif ext == 'pdf':
            pages = []
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    pages.append(page.extract_text() or "")
            return "\n".join(pages)
        elif ext in ('docx', 'doc'):
            doc = docx.Document(filepath)
            return "\n".join([para.text for para in doc.paragraphs])
        elif ext in config.IMAGE_EXTENSIONS:
            return None  # Will be handled by vision model
        else:
            return None
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def resize_and_compress_image(filepath, max_size=(1024, 1024), quality=85):
    """Resize image to reduce base64 size."""
    try:
        with Image.open(filepath) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            if img.mode in ('RGBA', 'P'): 
                img = img.convert('RGB')
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        logging.exception(f"Error compressing image: {e}")
        return None

def cleanup_old_uploads(upload_dir):
    try:
        now = time.time()
        for filename in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, filename)
            if os.path.isfile(filepath):
                if os.stat(filepath).st_mtime < now - 24 * 3600:
                    os.remove(filepath)
                    logging.info(f"Cleaned up old file: {filename}")
    except Exception as e:
        logging.error(f"Error in cleanup: {e}")
