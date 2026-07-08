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

def get_ollama_embedding(text, model=None):
    """Generate embeddings for text using the local Ollama instance."""
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
        print(f"Error generating embedding in get_ollama_embedding: {e}")
        return None

def get_ollama_embeddings_batch(texts, model=None):
    """Generate embeddings for a list of texts in a single batch call using Ollama /api/embed."""
    if not texts:
        return []
        
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
        print(f"Error generating batch embedding (Ollama /api/embed): {e}. Falling back to sequential embeddings.")
        # Fallback to sequential calls with same-length list mapping (including None for failures)
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

