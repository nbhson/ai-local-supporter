import os

UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'docx', 'doc', 'md', 'csv', 'json', 'xml', 'yaml', 'yml',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp'
}

# Ollama configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen2.5-coder:14b")
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", 8192))

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp'}
VISION_MODELS = {'qwen2.5-vl', 'qwen2.5vl', 'llava', 'bakllava', 'moondream', 'cog-vlm'}
