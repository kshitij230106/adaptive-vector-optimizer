import os

import chromadb
from sentence_transformers import SentenceTransformer

from services.keyword_service import keyword_search, mark_index_dirty

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

    # Notify the keyword index that data has changed

    mark_index_dirty()


# ============================================================
# SEARCH EMBEDDINGS (VECTOR ONLY)
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


# ============================================================
# HYBRID SEARCH
# ============================================================


def hybrid_search(query, n_results=5, alpha=0.7):
    """
    Combines vector similarity search with BM25 keyword
    search using score fusion.

    Parameters:
        query:     The search query string.
        n_results: Number of results to return.
        alpha:     Weight for vector scores (0.0 to 1.0).
                   1.0 = pure vector, 0.0 = pure keyword.

    Returns:
        Fused and ranked list of result dicts.
    """

    # Clamp alpha to valid range

    alpha = max(0.0, min(1.0, alpha))

    # --------------------------------------------------------
    # Run both searches
    # --------------------------------------------------------

    # Fetch extra results to improve fusion quality

    fetch_count = n_results * 2

    vector_results = search_embeddings(query, n_results=fetch_count)

    bm25_results = keyword_search(query, collection, n_results=fetch_count)

    # --------------------------------------------------------
    # Normalize scores to [0, 1]
    # --------------------------------------------------------

    def normalize_scores(results, score_key):

        if not results:
            return results

        scores = [r[score_key] for r in results]

        min_score = min(scores)
        max_score = max(scores)

        score_range = max_score - min_score

        for r in results:

            if score_range > 0:

                r["normalized_score"] = (
                    (r[score_key] - min_score) / score_range
                )

            else:

                r["normalized_score"] = 1.0

        return results

    vector_results = normalize_scores(vector_results, "score")

    bm25_results = normalize_scores(bm25_results, "bm25_score")

    # --------------------------------------------------------
    # Fuse results by document text fingerprint
    # --------------------------------------------------------

    fused = {}

    for r in vector_results:

        fingerprint = r["text"].strip().lower()[:200]

        fused[fingerprint] = {
            "text": r["text"],
            "source": r["source"],
            "chunk_number": r["chunk_number"],
            "vector_score": r.get("normalized_score", 0.0),
            "bm25_score": 0.0,
        }

    for r in bm25_results:

        fingerprint = r["text"].strip().lower()[:200]

        if fingerprint in fused:

            fused[fingerprint]["bm25_score"] = r.get(
                "normalized_score", 0.0
            )

        else:

            fused[fingerprint] = {
                "text": r["text"],
                "source": r["source"],
                "chunk_number": r["chunk_number"],
                "vector_score": 0.0,
                "bm25_score": r.get("normalized_score", 0.0),
            }

    # --------------------------------------------------------
    # Compute fused score
    # --------------------------------------------------------

    results = []

    for entry in fused.values():

        fused_score = (
            alpha * entry["vector_score"]
            + (1 - alpha) * entry["bm25_score"]
        )

        results.append({
            "text": entry["text"],
            "score": round(fused_score, 6),
            "vector_score": round(entry["vector_score"], 6),
            "bm25_score": round(entry["bm25_score"], 6),
            "source": entry["source"],
            "chunk_number": entry["chunk_number"],
            "search_mode": "hybrid",
        })

    # Sort by fused score descending

    results.sort(key=lambda r: r["score"], reverse=True)

    return results[:n_results]
