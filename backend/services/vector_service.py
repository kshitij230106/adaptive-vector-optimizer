import os

import chromadb
from sentence_transformers import SentenceTransformer

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")


# ============================================================
# CHROMADB
# ============================================================

client = chromadb.PersistentClient(path=CHROMA_PATH)


collection = client.get_or_create_collection(name="document_embeddings")


# ============================================================
# EMBEDDING MODEL
# ============================================================

model = SentenceTransformer("BAAI/bge-base-en-v1.5")


# ============================================================
# GET COLLECTION
# ============================================================


def get_collection():

    return collection


# ============================================================
# GENERATE EMBEDDINGS
# ============================================================


def generate_embeddings(chunks):

    if not chunks:

        return []

    # IMPORTANT:
    # encode() converts text into numerical vectors

    embeddings = model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)

    # Convert numpy arrays into normal Python lists

    embeddings = embeddings.tolist()

    return embeddings


# ============================================================
# STORE EMBEDDINGS
# ============================================================


def store_embeddings(embeddings, chunks, filename):

    if not chunks:

        return

    if not embeddings:

        raise ValueError("No embeddings were generated.")

    if len(embeddings) != len(chunks):

        raise ValueError("Number of embeddings does not match " "number of chunks.")

    # Unique IDs for every chunk

    ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]

    # Metadata for every chunk

    metadatas = [{"source": filename, "chunk_number": i} for i in range(len(chunks))]

    # Store everything in ChromaDB

    collection.upsert(
        ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas
    )


# ============================================================
# SEARCH EMBEDDINGS
# ============================================================


def search_embeddings(query, n_results=5):

    # Generate embedding for the search query

    query_embedding = model.encode(
        query, convert_to_numpy=True, normalize_embeddings=True
    ).tolist()

    # Search ChromaDB

    search_result = collection.query(
        query_embeddings=[query_embedding], n_results=n_results
    )

    documents = search_result.get("documents", [[]])[0]

    distances = search_result.get("distances", [[]])[0]

    metadatas = search_result.get("metadatas", [[]])[0]

    results = []

    for i in range(len(documents)):

        distance = distances[i]

        metadata = metadatas[i] if i < len(metadatas) else {}

        # Convert distance into a simple score

        score = 1 / (1 + distance)

        results.append(
            {
                "text": documents[i],
                "distance": float(distance),
                "score": float(score),
                "source": metadata.get("source", "Unknown"),
                "chunk_number": metadata.get("chunk_number", "Unknown"),
            }
        )

    return results
