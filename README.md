# Adaptive Vector Optimizer

An intelligent document processing and semantic search system built using **FastAPI, Sentence Transformers, and ChromaDB**.

The project allows users to upload documents, extract their text, divide the content into smaller chunks, convert those chunks into vector embeddings, store them in ChromaDB, and perform semantic searches over the uploaded documents.

## 🚀 Features

- 📄 Upload and process documents
- 🔍 Semantic search using vector embeddings
- 🧠 BGE-based embedding model
- 🗃️ Persistent vector storage using ChromaDB
- ✂️ Configurable text chunking
- 📊 Search results with similarity scores
- 📁 View uploaded documents
- 🌐 Simple web-based frontend
- ⚡ FastAPI backend with Swagger API documentation
- 🔄 Supports multiple document formats

### Supported File Formats

- .pdf
- .docx
- .pptx
- .txt
- .md

> Old .doc files are not directly supported. Convert .doc files to .docx before uploading.

## 🏗️ Project Structure


adaptive-vector-optimizer/
│
├── backend/
│   ├── app.py
│   ├── check_chroma.py
│   ├── clear_chroma.py
│   ├── database.py
│   ├── models.py
│   ├── requirements.txt
│   │
│   └── services/
│       ├── answer_service.py
│       ├── chunking_service.py
│       ├── document_processor.py
│       └── vector_service.py
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── .gitignore
└── README.md

🔄 How It Works
Document Upload
       ↓
Text Extraction
       ↓
Text Chunking
       ↓
Generate Embeddings
       ↓
Store Vectors in ChromaDB
       ↓
User Search Query
       ↓
Generate Query Embedding
       ↓
Semantic Vector Search
       ↓
Retrieve Relevant Chunks
       ↓
Display Results

🧠 Embedding Model
The project uses the following Sentence Transformer model:
BAAI/bge-base-en-v1.5

The model converts text into numerical vector representations that can be compared based on semantic similarity.
Embedding Dimension
768

Embeddings are normalized before being stored and searched.
🛠️ Technologies Used
Backend
- Python
- FastAPI
- Uvicorn
- Sentence Transformers
- ChromaDB
- PyMuPDF
- python-docx
- python-pptx
Frontend
- HTML
- CSS
- JavaScript
Vector Database
- ChromaDB
Embedding Model
- BAAI/bge-base-en-v1.5
📋 Requirements
Make sure the following are installed:
- Python 3.x
- Git
- Modern web browser
⚙️ Installation
1. Clone the Repository
git clone https://github.com/kshitij230106/adaptive-vector-optimizer.git

Move into the project directory:
cd adaptive-vector-optimizer

2. Create a Virtual Environment
Go to the backend directory:
cd backend

Create a virtual environment:
python -m venv venv

3. Activate the Virtual Environment
Windows PowerShell
.\venv\Scripts\Activate.ps1

Windows CMD
venv\Scripts\activate

4. Install Dependencies
pip install -r requirements.txt

▶️ Running the Backend
From the backend directory, run:
uvicorn app:app

The backend API will be available at:
http://127.0.0.1:8000

Swagger API Documentation
FastAPI provides interactive API documentation.
Open:
http://127.0.0.1:8000/docs

🌐 Running the Frontend
Open a new terminal.
Navigate to the frontend directory:
cd frontend

Start the frontend server:
python -m http.server 5500

Then open:
http://localhost:5500

🔌 API Endpoints
Health Check
GET /

Returns the API status.
Upload Document
POST /upload

Uploads and processes a document.
The upload process includes:
1. Saving the document
2. Extracting text
3. Creating text chunks
4. Generating embeddings
5. Storing embeddings in ChromaDB
Optional parameters:
chunk_size
overlap

Default values:
chunk_size = 1000
overlap = 100

Get Uploaded Documents
GET /documents

Returns the documents currently stored in the vector database.
Semantic Search
POST /search

Example request:
{
    "query": "database normalization",
    "n_results": 5
}

The system returns relevant document chunks along with:
- Source document
- Chunk number
- Distance
- Similarity score
- Retrieved text
📁 Document Processing
Different file formats are processed using format-specific extraction methods.
PDF
PDF files are processed using:
PyMuPDF

DOCX
DOCX files are processed using:
python-docx

Paragraphs and tables can be extracted.
PPTX
PPTX files are processed using:
python-pptx

Text from presentation slides is extracted.
TXT and Markdown
TXT and Markdown files are processed as text files.
DOC
Old .doc files are not directly supported.
They should be converted to:
.docx

before uploading.
✂️ Text Chunking
Large documents are divided into smaller chunks before generating embeddings.
Default configuration:
Chunk Size: 1000
Overlap: 100

Chunking allows the system to search smaller sections of documents rather than treating an entire document as one large piece of text.
🗃️ ChromaDB
ChromaDB is used as the persistent vector database.
Generated embeddings are stored along with metadata such as:
{
    "source": "document.pdf",
    "chunk_number": 0
}

The local ChromaDB directory is:
backend/chroma_db/

This directory is excluded from Git using .gitignore.
🔍 Semantic Search
Unlike traditional keyword search, semantic search converts both documents and user queries into vector representations.
For example, a query such as:
How does normalization reduce duplicate data?

can retrieve content related to:
Database normalization
Data redundancy
Functional dependencies
Normal forms

even when the exact words from the query are not present in the document.
🔐 Git Ignore
The project excludes generated and local files from Git.
Examples include:
backend/venv/
backend/chroma_db/
backend/data/
__pycache__/
*.pyc
.env
*.env
.vscode/
.idea/

This prevents large generated files, local environments, uploaded documents, and sensitive configuration files from being pushed to GitHub.
🧪 Development
Check the current Git status:
git status

Add changes:
git add .

Create a commit:
git commit -m "Describe your changes"

Push changes to GitHub:
git push

📌 Future Improvements
Possible future improvements include:
- 🤖 LLM-powered answer generation
- 🎯 Improved result reranking
- 📈 Vector search performance optimization
- 👤 User authentication
- 🗂️ Document management and deletion
- 📊 Search analytics
- 🔄 Automatic document re-indexing
- ☁️ Cloud deployment
- 🧠 Hybrid keyword + semantic search
- ⚡ Background document processing
👨‍💻 Project Information
Project Name: Adaptive Vector Optimizer
GitHub Repository:
https://github.com/kshitij230106/adaptive-vector-optimizer
📜 License
This project is intended for educational and project-development purposes.
