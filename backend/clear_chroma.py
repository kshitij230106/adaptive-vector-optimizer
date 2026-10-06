import chromadb

client = chromadb.PersistentClient(path="chroma_db")

# Delete the collection
client.delete_collection(name="documents")

print("ChromaDB collection cleared successfully!")