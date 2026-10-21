import chromadb
from sentence_transformers import SentenceTransformer


model = SentenceTransformer("BAAI/bge-base-en-v1.5")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="research_papers")

test_query = input("enter the query:")

print(f"Query: '{test_query}'\n")

results = collection.query(
    query_texts=[test_query],
    n_results=3
)

# 4. Print the results to inspect accuracy
for i, (text, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
    print(f"--- Result {i+1} (Source: {metadata['source']}) ---")
    print(text[:300] + "...\n") # Prints the first 300 characters of each chunk