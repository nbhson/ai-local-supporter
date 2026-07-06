import os
import requests
from flask import Flask, render_template, jsonify
from blueprints.doc import doc_bp
from blueprints.code import code_bp
import config

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register Blueprints
app.register_blueprint(doc_bp, url_prefix='/api/doc')
app.register_blueprint(code_bp, url_prefix='/api/code')

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