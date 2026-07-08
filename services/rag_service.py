import os
import requests
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
import config

# Initialize local ChromaDB persistent client
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Persistent session for connection pooling
rag_session = requests.Session()

_fastembed_model = None

def get_embedding_model():
    global _fastembed_model
    if _fastembed_model is None:
        from fastembed import TextEmbedding
        # BAAI/bge-small-en-v1.5 is default, extremely fast and accurate
        _fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _fastembed_model

def get_ollama_embedding(text, model=None):
    """Generate embeddings for text using fastembed on CPU. Falls back to Ollama if fastembed fails."""
    try:
        model_instance = get_embedding_model()
        embeddings = list(model_instance.embed([text]))
        if embeddings:
            return [float(x) for x in embeddings[0]]
    except Exception as e:
        print(f"fastembed error: {e}. Falling back to Ollama API.")
        
    model = model or config.EMBEDDING_MODEL
    url = f"{config.OLLAMA_URL.rstrip('/')}/embeddings"
    
    try:
        response = rag_session.post(
            url,
            json={"model": model, "prompt": text, "keep_alive": "15m"},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("embedding")
    except Exception as e:
        print(f"Error generating embedding in fallback Ollama: {e}")
        return None

def get_ollama_embeddings_batch(texts, model=None):
    """Generate embeddings for a list of texts using fastembed batching. Falls back to Ollama API."""
    if not texts:
        return []
    try:
        model_instance = get_embedding_model()
        embeddings = list(model_instance.embed(texts))
        return [[float(x) for x in emb] for emb in embeddings]
    except Exception as e:
        print(f"fastembed batch error: {e}. Falling back to Ollama API.")
        
    model = model or config.EMBEDDING_MODEL
    url = f"{config.OLLAMA_URL.rstrip('/')}/embed"
    
    try:
        response = rag_session.post(
            url,
            json={"model": model, "input": texts, "keep_alive": "15m"},
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("embeddings", [])
    except Exception as e:
        print(f"Error generating batch embedding fallback Ollama: {e}. Falling back to sequential embeddings.")
        embeddings = []
        for t in texts:
            vector = get_ollama_embedding(t, model)
            embeddings.append(vector)
        return embeddings

def index_document(session_id, text):
    """Split text into chunks, generate embeddings, and store in ChromaDB."""
    if not text or not text.strip():
        return 0
    
    # 1. Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.RAG_CHUNK_SIZE,
        chunk_overlap=config.RAG_CHUNK_OVERLAP
    )
    chunks = text_splitter.split_text(text)
    chunks = [c for c in chunks if c.strip()]
    if not chunks:
        return 0
    
    # 2. Get or create collection for this session
    collection_name = f"sess_{session_id}"
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    # 3. Store chunks and embeddings in batches
    documents = []
    embeddings = []
    ids = []
    
    batch_size = 32
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_vectors = get_ollama_embeddings_batch(batch_chunks)
        
        # Align chunks and vectors properly
        for idx, (chunk, vector) in enumerate(zip(batch_chunks, batch_vectors)):
            if vector:
                documents.append(chunk)
                embeddings.append(vector)
                ids.append(f"chunk_{i + idx}")
            
    if ids:
        collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids
        )
    return len(ids)

def retrieve_context(session_id, query, top_k=None):
    """Find the most similar chunks from ChromaDB for the given query."""
    if top_k is None:
        top_k = config.RAG_TOP_K
    query_vector = get_ollama_embedding(query)
    if not query_vector:
        return ""
        
    try:
        collection_name = f"sess_{session_id}"
        collection = chroma_client.get_collection(name=collection_name)
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k
        )
        
        # Results['documents'] is a list of lists of strings
        docs = results.get('documents', [[]])[0]
        return "\n\n---\n\n".join(docs)
    except Exception as e:
        print(f"Error retrieving context for session {session_id}: {e}")
        return ""

