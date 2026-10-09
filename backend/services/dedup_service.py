import hashlib
import math


# ============================================================
# DUPLICATE DETECTION SERVICE
# ============================================================
#
# Identifies and removes duplicate or near-duplicate
# document chunks. Operates at two levels:
#
# 1. Ingest-time:  Prevents duplicate chunks from being
#                  stored in ChromaDB.
# 2. Search-time:  Removes near-duplicate results to
#                  improve answer diversity.
# ============================================================


# ============================================================
# CONTENT HASHING (EXACT DUPLICATES)
# ============================================================


def compute_content_hash(text):
    """
    Computes a SHA-256 hash of normalized text content.
    Normalization: lowercase, strip whitespace, collapse
    multiple spaces.
    """

    normalized = " ".join(text.lower().split())

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def deduplicate_chunks_exact(chunks):
    """
    Removes exact duplicate chunks based on content hash.

    Returns:
        unique_chunks: List of unique chunks.
        removed_count: Number of duplicates removed.
        hash_map:      Dict mapping hash → chunk index.
    """

    seen_hashes = {}

    unique_chunks = []

    removed_count = 0

    for i, chunk in enumerate(chunks):

        content_hash = compute_content_hash(chunk)

        if content_hash in seen_hashes:

            removed_count += 1

        else:

            seen_hashes[content_hash] = len(unique_chunks)

            unique_chunks.append(chunk)

    return {
        "unique_chunks": unique_chunks,
        "removed_count": removed_count,
        "hash_map": seen_hashes,
    }


# ============================================================
# COSINE SIMILARITY
# ============================================================


def cosine_similarity(vec_a, vec_b):
    """
    Computes cosine similarity between two vectors.
    Returns a float in [-1, 1].
    """

    if len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))

    norm_a = math.sqrt(sum(a * a for a in vec_a))

    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


# ============================================================
# NEAR-DUPLICATE DETECTION (EMBEDDING-BASED)
# ============================================================


def find_near_duplicates(embeddings, threshold=0.95):
    """
    Finds pairs of near-duplicate chunks based on
    cosine similarity of their embeddings.

    Parameters:
        embeddings: List of embedding vectors.
        threshold:  Cosine similarity threshold above which
                    two chunks are considered near-duplicates.

    Returns:
        duplicate_pairs: List of (index_i, index_j, similarity)
        duplicate_indices: Set of indices to remove (keeps first)
    """

    n = len(embeddings)

    duplicate_pairs = []

    duplicate_indices = set()

    for i in range(n):

        if i in duplicate_indices:
            continue

        for j in range(i + 1, n):

            if j in duplicate_indices:
                continue

            similarity = cosine_similarity(
                embeddings[i], embeddings[j]
            )

            if similarity >= threshold:

                duplicate_pairs.append((i, j, similarity))

                # Mark the later index as duplicate

                duplicate_indices.add(j)

    return {
        "duplicate_pairs": duplicate_pairs,
        "duplicate_indices": duplicate_indices,
    }


# ============================================================
# DEDUPLICATE AT INGEST TIME
# ============================================================


def deduplicate_chunks_at_ingest(chunks, embeddings, similarity_threshold=0.95):
    """
    Full deduplication pipeline for document ingestion.

    1. First removes exact duplicates via content hashing.
    2. Then removes near-duplicates via embedding similarity.

    Returns:
        unique_chunks:     Deduplicated chunk texts.
        unique_embeddings: Corresponding embeddings.
        stats:             Deduplication statistics.
    """

    original_count = len(chunks)

    # --------------------------------------------------------
    # Step 1: Exact deduplication
    # --------------------------------------------------------

    exact_result = deduplicate_chunks_exact(chunks)

    exact_unique = exact_result["unique_chunks"]

    exact_removed = exact_result["removed_count"]

    # Build corresponding embeddings list for unique chunks

    # We need to map unique chunks back to their embeddings

    hash_to_embedding = {}

    for i, chunk in enumerate(chunks):

        content_hash = compute_content_hash(chunk)

        if content_hash not in hash_to_embedding:

            hash_to_embedding[content_hash] = embeddings[i]

    exact_unique_embeddings = [
        hash_to_embedding[compute_content_hash(chunk)]
        for chunk in exact_unique
    ]

    # --------------------------------------------------------
    # Step 2: Near-duplicate detection
    # --------------------------------------------------------

    if len(exact_unique_embeddings) > 1:

        near_result = find_near_duplicates(
            exact_unique_embeddings,
            threshold=similarity_threshold,
        )

        near_duplicate_indices = near_result["duplicate_indices"]

    else:

        near_duplicate_indices = set()

    # Filter out near-duplicates

    final_chunks = []

    final_embeddings = []

    for i, (chunk, embedding) in enumerate(
        zip(exact_unique, exact_unique_embeddings)
    ):

        if i not in near_duplicate_indices:

            final_chunks.append(chunk)

            final_embeddings.append(embedding)

    near_removed = len(near_duplicate_indices)

    # --------------------------------------------------------
    # Compile stats
    # --------------------------------------------------------

    stats = {
        "original_count": original_count,
        "exact_duplicates_removed": exact_removed,
        "near_duplicates_removed": near_removed,
        "total_removed": exact_removed + near_removed,
        "final_count": len(final_chunks),
        "similarity_threshold": similarity_threshold,
    }

    return {
        "unique_chunks": final_chunks,
        "unique_embeddings": final_embeddings,
        "stats": stats,
    }


# ============================================================
# DEDUPLICATE SEARCH RESULTS
# ============================================================


def deduplicate_search_results(results, similarity_threshold=0.90):
    """
    Removes near-duplicate results from search output
    to improve answer diversity.

    Uses text-based similarity (Jaccard) since we may
    not have embeddings for search results.

    Parameters:
        results:   List of result dicts with "text" key.
        similarity_threshold: Text similarity threshold.

    Returns:
        Deduplicated list of results.
    """

    if not results or len(results) <= 1:
        return results

    unique_results = [results[0]]

    for candidate in results[1:]:

        is_duplicate = False

        candidate_text = candidate.get("text", "")

        candidate_words = set(candidate_text.lower().split())

        for existing in unique_results:

            existing_text = existing.get("text", "")

            existing_words = set(existing_text.lower().split())

            # Jaccard similarity

            intersection = len(candidate_words & existing_words)

            union = len(candidate_words | existing_words)

            if union > 0:

                similarity = intersection / union

                if similarity >= similarity_threshold:

                    is_duplicate = True

                    break

        if not is_duplicate:

            unique_results.append(candidate)

    return unique_results
