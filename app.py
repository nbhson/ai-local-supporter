import os
import requests
from flask import Flask, render_template, jsonify
from blueprints.doc import doc_bp
from blueprints.code import code_bp
from blueprints.chat import chat_bp
from services.database import db
import config

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CELERY_BROKER_URL'] = config.CELERY_BROKER_URL
app.config['CELERY_RESULT_BACKEND'] = config.CELERY_RESULT_BACKEND

# Initialize DB
db.init_app(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create tables
with app.app_context():
    db.create_all()

# Register Blueprints
app.register_blueprint(doc_bp, url_prefix='/api/doc')
app.register_blueprint(code_bp, url_prefix='/api/code')
app.register_blueprint(chat_bp, url_prefix='/api/chat')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models', methods=['GET'])
def list_models():
    try:
        response = requests.get(f"{config.OLLAMA_URL}/tags", timeout=10)
        response.raise_for_status()
        models_data = response.json()
        model_list = [m['name'] for m in models_data.get('models', [])]
        return jsonify({"models": model_list})
    except Exception:
        return jsonify({"models": [config.DEFAULT_MODEL]})

if __name__ == '__main__':
    print("🚀 Starting AI Local Support")
    print("📁 Modules: Document Analysis + Code Analysis")
    print(f"🌐 Open http://127.0.0.1:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)