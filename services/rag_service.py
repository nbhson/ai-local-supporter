import os
import requests
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
import config

# Initialize local ChromaDB persistent client
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

def get_ollama_embedding(text, model=None):
    """Generate embeddings for text using the local Ollama instance."""
    model = model or config.EMBEDDING_MODEL
    url = f"{config.OLLAMA_URL.rstrip('/')}/embeddings"
    
    try:
        response = requests.post(
            url,
            json={"model": model, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("embedding")
    except Exception as e:
        print(f"Error generating embedding in get_ollama_embedding: {e}")
        return None

def index_document(session_id, text):
    """Split text into chunks, generate embeddings, and store in ChromaDB."""
    if not text or not text.strip():
        return 0
    
    # 1. Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_text(text)
    
    # 2. Get or create collection for this session
    collection_name = f"sess_{session_id}"
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    # 3. Store chunks and embeddings
    documents = []
    embeddings = []
    ids = []
    
    for idx, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        vector = get_ollama_embedding(chunk)
        if vector:
            documents.append(chunk)
            embeddings.append(vector)
            ids.append(f"chunk_{idx}")
            
    if ids:
        collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids
        )
    return len(ids)

def retrieve_context(session_id, query, top_k=4):
    """Find the most similar chunks from ChromaDB for the given query."""
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
