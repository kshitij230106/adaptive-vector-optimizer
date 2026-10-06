import os
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from services.document_processor import extract_text
from services.chunking_service import create_chunks
from services.vector_service import (
    generate_embeddings,
    store_embeddings,
    search_embeddings,
)

# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Adaptive Vector Index Optimizer",
    description="Semantic document search using BGE embeddings and ChromaDB",
    version="1.0.0",
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
# SEARCH REQUEST
# ============================================================


class SearchRequest(BaseModel):

    query: str

    n_results: int = 5


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
    file: UploadFile = File(...), chunk_size: int = 1000, overlap: int = 100
):

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

    if chunk_size < 100:

        raise HTTPException(status_code=400, detail="Chunk size must be at least 100.")

    if overlap < 0:

        raise HTTPException(status_code=400, detail="Overlap cannot be negative.")

    if overlap >= chunk_size:

        raise HTTPException(
            status_code=400, detail="Overlap must be smaller than chunk size."
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
                status_code=400, detail="No text could be extracted from the document."
            )

        # ----------------------------------------------------
        # Create chunks
        # ----------------------------------------------------

        chunks = create_chunks(extracted_text, chunk_size, overlap)

        if not chunks:

            raise HTTPException(
                status_code=400, detail="No chunks were created from the document."
            )

        # ----------------------------------------------------
        # Generate embeddings
        # ----------------------------------------------------

        embeddings = generate_embeddings(chunks)

        # ----------------------------------------------------
        # Store embeddings in ChromaDB
        # ----------------------------------------------------

        store_embeddings(embeddings, chunks, safe_filename)

        # ----------------------------------------------------
        # Return processing information
        # ----------------------------------------------------

        embedding_dimension = 0

        if embeddings:

            embedding_dimension = len(embeddings[0])

        return {
            "message": "Document uploaded and processed successfully.",
            "filename": safe_filename,
            "file_type": file_extension,
            "characters_extracted": len(extracted_text),
            "chunk_size": chunk_size,
            "overlap": overlap,
            "number_of_chunks": len(chunks),
            "number_of_embeddings": len(embeddings),
            "chunks_stored_in_chromadb": True,
            "embedding_dimension": embedding_dimension,
        }

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

        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    try:

        results = search_embeddings(request.query, request.n_results)

        return {"query": request.query, "results": results}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))
