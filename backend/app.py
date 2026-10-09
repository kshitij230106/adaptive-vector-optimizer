import os
import shutil
import time

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from typing import Optional

from services.document_processor import extract_text
from services.chunking_service import create_chunks
from services.adaptive_chunking_service import (
    create_adaptive_chunks,
    get_chunking_stats,
)
from services.vector_service import (
    generate_embeddings,
    store_embeddings,
    search_embeddings,
    hybrid_search,
)
from services.dedup_service import (
    deduplicate_chunks_at_ingest,
    deduplicate_search_results,
)
from services.query_optimizer import (
    optimize_query,
    merge_search_results,
)
from services.cache_service import search_cache


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Adaptive Vector Index Optimizer",
    description="Semantic document search using BGE embeddings and ChromaDB",
    version="2.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


DATA_DIR = os.path.join(BASE_DIR, "data")


os.makedirs(DATA_DIR, exist_ok=True)


# ============================================================
# ALLOWED FILE TYPES
# ============================================================

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".pptx", ".txt", ".md"}


# ============================================================
# REQUEST MODELS
# ============================================================


class SearchRequest(BaseModel):

    query: str

    n_results: int = 5

    search_mode: str = "hybrid"  # "vector", "keyword", "hybrid"

    alpha: float = 0.7  # Hybrid search weight (vector vs keyword)

    optimize_query: bool = True  # Enable query optimization

    deduplicate: bool = True  # Enable result deduplication


# ============================================================
# ROOT
# ============================================================


@app.get("/")
def root():

    return {"message": "Adaptive Vector Index Optimizer API is running"}


# ============================================================
# UPLOAD
# ============================================================


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = 1000,
    overlap: int = 100,
    chunking_mode: str = Query(
        default="adaptive",
        description="Chunking strategy: 'fixed' or 'adaptive'",
    ),
    enable_dedup: bool = Query(
        default=True,
        description="Enable duplicate chunk detection and removal",
    ),
    similarity_threshold: float = Query(
        default=0.95,
        description="Cosine similarity threshold for near-duplicate detection (0.0 to 1.0)",
    ),
):

    start_time = time.time()

    # --------------------------------------------------------
    # Validate filename
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(status_code=400, detail="No filename provided.")

    # --------------------------------------------------------
    # Validate extension
    # --------------------------------------------------------

    safe_filename = os.path.basename(file.filename)

    file_extension = os.path.splitext(safe_filename)[1].lower()

    if file_extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Allowed types: PDF, DOC, DOCX, PPTX, TXT and MD."
            ),
        )

    # --------------------------------------------------------
    # Validate chunk settings
    # --------------------------------------------------------

    if chunking_mode == "fixed":

        if chunk_size < 100:

            raise HTTPException(
                status_code=400, detail="Chunk size must be at least 100."
            )

        if overlap < 0:

            raise HTTPException(
                status_code=400, detail="Overlap cannot be negative."
            )

        if overlap >= chunk_size:

            raise HTTPException(
                status_code=400,
                detail="Overlap must be smaller than chunk size.",
            )

    # --------------------------------------------------------
    # Validate chunking mode
    # --------------------------------------------------------

    if chunking_mode not in ("fixed", "adaptive"):

        raise HTTPException(
            status_code=400,
            detail="chunking_mode must be 'fixed' or 'adaptive'.",
        )

    # --------------------------------------------------------
    # Save uploaded file
    # --------------------------------------------------------

    file_path = os.path.join(DATA_DIR, safe_filename)

    try:

        with open(file_path, "wb") as buffer:

            shutil.copyfileobj(file.file, buffer)

        # ----------------------------------------------------
        # Extract text
        # ----------------------------------------------------

        extracted_text = extract_text(file_path)

        if not extracted_text.strip():

            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from the document.",
            )

        # ----------------------------------------------------
        # Create chunks (fixed or adaptive)
        # ----------------------------------------------------

        chunking_stats = None

        if chunking_mode == "adaptive":

            chunks = create_adaptive_chunks(extracted_text)

            chunking_stats = get_chunking_stats(chunks)

        else:

            chunks = create_chunks(extracted_text, chunk_size, overlap)

        if not chunks:

            raise HTTPException(
                status_code=400,
                detail="No chunks were created from the document.",
            )

        # ----------------------------------------------------
        # Generate embeddings
        # ----------------------------------------------------

        embeddings = generate_embeddings(chunks)

        # ----------------------------------------------------
        # Deduplicate chunks (if enabled)
        # ----------------------------------------------------

        dedup_stats = None

        if enable_dedup and len(chunks) > 1:

            dedup_result = deduplicate_chunks_at_ingest(
                chunks, embeddings, similarity_threshold=similarity_threshold
            )

            chunks = dedup_result["unique_chunks"]

            embeddings = dedup_result["unique_embeddings"]

            dedup_stats = dedup_result["stats"]

        # ----------------------------------------------------
        # Store embeddings in ChromaDB
        # ----------------------------------------------------

        store_embeddings(embeddings, chunks, safe_filename)

        # ----------------------------------------------------
        # Invalidate search cache (stale results)
        # ----------------------------------------------------

        search_cache.invalidate_all()

        # ----------------------------------------------------
        # Return processing information
        # ----------------------------------------------------

        processing_time = round(time.time() - start_time, 3)

        embedding_dimension = 0

        if embeddings:

            embedding_dimension = len(embeddings[0])

        response = {
            "message": "Document uploaded and processed successfully.",
            "filename": safe_filename,
            "file_type": file_extension,
            "characters_extracted": len(extracted_text),
            "chunking_mode": chunking_mode,
            "chunk_size": chunk_size if chunking_mode == "fixed" else "auto",
            "overlap": overlap if chunking_mode == "fixed" else "adaptive",
            "number_of_chunks": len(chunks),
            "number_of_embeddings": len(embeddings),
            "chunks_stored_in_chromadb": True,
            "embedding_dimension": embedding_dimension,
            "processing_time_seconds": processing_time,
        }

        if chunking_stats:
            response["chunking_stats"] = chunking_stats

        if dedup_stats:
            response["dedup_stats"] = dedup_stats

        return response

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# GET UPLOADED DOCUMENTS
# ============================================================


@app.get("/documents")
def get_uploaded_documents():

    try:

        from services.vector_service import get_collection

        collection = get_collection()

        result = collection.get(include=["metadatas"])

        metadatas = result.get("metadatas", [])

        filenames = set()

        for metadata in metadatas:

            if not metadata:

                continue

            filename = metadata.get("source")

            if filename:

                filenames.add(filename)

        documents = sorted(list(filenames))

        return {"documents": documents, "count": len(documents)}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SEARCH
# ============================================================


@app.post("/search")
def search_documents(request: SearchRequest):

    if not request.query.strip():

        raise HTTPException(
            status_code=400, detail="Search query cannot be empty."
        )

    # --------------------------------------------------------
    # Validate search mode
    # --------------------------------------------------------

    valid_modes = ("vector", "keyword", "hybrid")

    if request.search_mode not in valid_modes:

        raise HTTPException(
            status_code=400,
            detail=f"search_mode must be one of: {', '.join(valid_modes)}",
        )

    try:

        start_time = time.time()

        # ----------------------------------------------------
        # Check cache first
        # ----------------------------------------------------

        cache_key_params = {
            "n_results": request.n_results,
            "search_mode": request.search_mode,
            "alpha": request.alpha,
            "optimize": request.optimize_query,
            "dedup": request.deduplicate,
        }

        cached_result = search_cache.get(
            request.query, **cache_key_params
        )

        if cached_result is not None:

            cached_result["cache_hit"] = True

            cached_result["response_time_ms"] = round(
                (time.time() - start_time) * 1000, 2
            )

            return cached_result

        # ----------------------------------------------------
        # Query optimization
        # ----------------------------------------------------

        query_info = None

        if request.optimize_query:

            query_info = optimize_query(request.query)

            search_query = query_info["optimized"]

        else:

            search_query = request.query

        # ----------------------------------------------------
        # Execute search based on mode
        # ----------------------------------------------------

        if request.search_mode == "hybrid":

            results = hybrid_search(
                search_query,
                n_results=request.n_results,
                alpha=request.alpha,
            )

        elif request.search_mode == "keyword":

            from services.keyword_service import keyword_search
            from services.vector_service import get_collection

            collection = get_collection()

            results = keyword_search(
                search_query, collection, n_results=request.n_results
            )

            # Add a unified score key for consistency

            for r in results:
                r["score"] = r.get("bm25_score", 0.0)
                r["search_mode"] = "keyword"

        else:

            results = search_embeddings(
                search_query, n_results=request.n_results
            )

            for r in results:
                r["search_mode"] = "vector"

        # ----------------------------------------------------
        # Multi-query search (if optimized and has variants)
        # ----------------------------------------------------

        if (
            request.optimize_query
            and query_info
            and len(query_info.get("variants", [])) > 1
        ):

            all_result_sets = [results]

            for variant in query_info["variants"][1:]:

                if request.search_mode == "hybrid":

                    variant_results = hybrid_search(
                        variant,
                        n_results=request.n_results,
                        alpha=request.alpha,
                    )

                elif request.search_mode == "keyword":

                    from services.keyword_service import keyword_search
                    from services.vector_service import get_collection

                    collection = get_collection()

                    variant_results = keyword_search(
                        variant, collection, n_results=request.n_results
                    )

                else:

                    variant_results = search_embeddings(
                        variant, n_results=request.n_results
                    )

                all_result_sets.append(variant_results)

            results = merge_search_results(
                all_result_sets, max_results=request.n_results
            )

        # ----------------------------------------------------
        # Deduplicate results
        # ----------------------------------------------------

        if request.deduplicate and results:

            results = deduplicate_search_results(results)

            # Trim to requested count after dedup

            results = results[: request.n_results]

        # ----------------------------------------------------
        # Build response
        # ----------------------------------------------------

        response_time = round((time.time() - start_time) * 1000, 2)

        response = {
            "query": request.query,
            "search_mode": request.search_mode,
            "results": results,
            "result_count": len(results),
            "response_time_ms": response_time,
            "cache_hit": False,
        }

        if query_info:

            response["query_optimization"] = {
                "original": query_info["original"],
                "optimized": query_info["optimized"],
                "variants_used": query_info["variants"],
                "key_terms": query_info["key_terms"],
            }

        # ----------------------------------------------------
        # Cache the result
        # ----------------------------------------------------

        search_cache.set(
            request.query, response, **cache_key_params
        )

        return response

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# CACHE STATS
# ============================================================


@app.get("/cache/stats")
def get_cache_stats():
    """
    Returns cache performance statistics including
    hit rate, size, and eviction count.
    """

    return search_cache.get_stats()


# ============================================================
# CACHE CLEAR
# ============================================================


@app.post("/cache/clear")
def clear_cache():
    """
    Manually clears the entire search cache.
    """

    search_cache.invalidate_all()

    return {"message": "Cache cleared successfully."}


# ============================================================
# CACHE ENTRIES
# ============================================================


@app.get("/cache/entries")
def get_cache_entries():
    """
    Returns a list of currently cached queries
    and their access metadata.
    """

    entries = search_cache.get_cached_queries()

    return {"entries": entries, "count": len(entries)}
