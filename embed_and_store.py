import os
import chromadb
from sentence_transformers import SentenceTransformer

# 1. Initialize the Chroma vector database locally
client = chromadb.PersistentClient(path="./chroma_db")

# Create or get your collection
collection = client.get_or_create_collection(name="research_papers")

# 2. Load a lightweight, high-performing embedding model
# (e.g., BGE-base or all-MiniLM-L6-v2)
print("Loading embedding model...")
model = SentenceTransformer("BAAI/bge-base-en-v1.5")

# 3. Read your chunk files and add them to the database
CHUNKS_FOLDER = "chunks_output"

for filename in os.listdir(CHUNKS_FOLDER):
    if filename.endswith("_chunks.txt"):
        file_path = os.path.join(CHUNKS_FOLDER, filename)
        print(f"Embedding and storing: {filename}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Split the file back into individual chunks using our separator
        raw_chunks = content.split("--- CHUNK ")
        
        documents = []
        metadatas = []
        ids = []
        
        for chunk_text in raw_chunks:
            if not chunk_text.strip():
                continue
            
            # Extract chunk number and actual text
            lines = chunk_text.split(" ---\n", 1)
            if len(lines) == 2:
                chunk_num, text = lines
                chunk_id = f"{filename}_chunk_{chunk_num}"
                
                documents.append(text.strip())
                metadatas.append({"source": filename})
                ids.append(chunk_id)
        
        # Add to ChromaDB (it automatically handles generating the vector embeddings)
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

print("All chunks successfully embedded and stored in ChromaDB!")