import os

UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'docx', 'doc', 'md', 'csv', 'json', 'xml', 'yaml', 'yml',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp'
}

# Ollama configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen2.5-coder:14b")
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", 8192))

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp'}
VISION_MODELS = {'qwen2.5-vl', 'qwen2.5vl', 'llava', 'bakllava', 'moondream', 'cog-vlm'}

# Database & Celery Configuration
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///ai_local_support.db")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Embedding Configuration for RAG
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

# Refactoring Readability & Magic Numbers Config
AGENT_MAX_ITERATIONS = 10
AGENT_MAX_DEPTH = 2
AGENT_MAX_ENTRIES_PER_DIR = 30
RAG_TOP_K = 4
RAG_CHUNK_SIZE = 1000
RAG_CHUNK_OVERLAP = 200
IMAGE_COMPRESS_MAX_SIZE = (1024, 1024)
IMAGE_COMPRESS_QUALITY = 85
CLEANUP_EXPIRE_SECONDS = 24 * 3600  # 1 day
CHAT_HISTORY_LIMIT = 10
PROJECT_HISTORY_LIMIT = 8
MAX_TEXT_CHARS = 15000

EXCLUDE_DIRS = {
    '.git', 'node_modules', '.venv', 'venv', 'env', '.idea', '__pycache__', 
    'dist', 'build', 'target', '.npm', '.cache', '.angular', '.next', '.nuxt',
    '.sass-cache', '.svelte-kit', '.agents', '.gemini', 'coverage', '.nyc_output'
}
EXCLUDE_FILES = {'.DS_Store', 'Thumbs.db'}


