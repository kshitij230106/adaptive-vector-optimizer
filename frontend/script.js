// ============================================================
// ADAPTIVE VECTOR OPTIMIZER - FRONTEND
// ============================================================


// API URL

const API_URL = "http://127.0.0.1:8000";


// Allowed file extensions

const allowedExtensions = [
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".md"
];


// ============================================================
// GET HTML ELEMENTS
// ============================================================

const fileInput = document.getElementById("fileInput");

const selectedFiles = document.getElementById("selectedFiles");

const chunkSizeInput = document.getElementById("chunkSize");

const overlapInput = document.getElementById("overlap");

const uploadBtn = document.getElementById("uploadBtn");

const uploadStatus = document.getElementById("uploadStatus");

const uploadedFiles = document.getElementById("uploadedFiles");

const processingResults = document.getElementById("processingResults");

const queryInput = document.getElementById("queryInput");

const searchBtn = document.getElementById("searchBtn");

const results = document.getElementById("results");


// ============================================================
// CHECK FRONTEND
// ============================================================

console.log("Frontend loaded successfully.");

console.log("fileInput:", fileInput);

console.log("uploadBtn:", uploadBtn);

console.log("queryInput:", queryInput);

console.log("searchBtn:", searchBtn);


// ============================================================
// FILE SELECTION
// ============================================================

fileInput.addEventListener("change", function () {

    const file = fileInput.files[0];


    if (!file) {

        selectedFiles.innerHTML = `
            <p class="empty-message">
                No file selected.
            </p>
        `;

        return;
    }


    selectedFiles.innerHTML = `
        <div class="selected-file">
            📄 <strong>${escapeHtml(file.name)}</strong>
            <br>
            <small>
                ${getFileExtension(file.name).toUpperCase()}
                -
                ${formatFileSize(file.size)}
            </small>
        </div>
    `;

});


// ============================================================
// UPLOAD DOCUMENT
// ============================================================

uploadBtn.addEventListener("click", async function () {

    const file = fileInput.files[0];


    // Check file

    if (!file) {

        uploadStatus.textContent =
            "Please select a document first.";

        return;
    }


    // Check extension

    const extension = getFileExtension(file.name);


    if (!allowedExtensions.includes(extension)) {

        uploadStatus.textContent =
            "Unsupported file type.";

        return;
    }


    // Get chunk settings

    const chunkSize =
        parseInt(chunkSizeInput.value);

    const overlap =
        parseInt(overlapInput.value);


    // Validate chunk size

    if (isNaN(chunkSize) || chunkSize < 100) {

        uploadStatus.textContent =
            "Chunk size must be at least 100.";

        return;
    }


    // Validate overlap

    if (isNaN(overlap) || overlap < 0) {

        uploadStatus.textContent =
            "Chunk overlap cannot be negative.";

        return;
    }


    if (overlap >= chunkSize) {

        uploadStatus.textContent =
            "Chunk overlap must be smaller than chunk size.";

        return;
    }


    // Disable button

    uploadBtn.disabled = true;

    uploadBtn.textContent = "Processing...";


    uploadStatus.textContent =
        `Uploading ${file.name}...`;


    try {

        const formData = new FormData();

        formData.append("file", file);


        // Send file to backend

        const response = await fetch(
            `${API_URL}/upload?chunk_size=${chunkSize}&overlap=${overlap}`,
            {
                method: "POST",
                body: formData
            }
        );


        const data = await response.json();


        // Check backend error

        if (!response.ok) {

            throw new Error(
                data.detail || "Upload failed."
            );
        }


        // Success

        uploadStatus.textContent =
            `✅ ${file.name} uploaded and processed successfully.`;


        // Clear selected file

        fileInput.value = "";


        selectedFiles.innerHTML = `
            <p class="empty-message">
                No file selected.
            </p>
        `;


        // Refresh uploaded document list

        await loadUploadedDocuments();


        // Add processing result

        addProcessingResult(data);


    } catch (error) {

        console.error("Upload error:", error);


        uploadStatus.textContent =
            `❌ Upload failed: ${error.message}`;

    }


    // Enable button again

    uploadBtn.disabled = false;

    uploadBtn.textContent =
        "Upload and Process";

});


// ============================================================
// LOAD UPLOADED DOCUMENTS
// ============================================================

async function loadUploadedDocuments() {

    try {

        const response = await fetch(
            `${API_URL}/documents`
        );


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail || "Could not load documents."
            );
        }


        displayUploadedDocuments(data.documents);


    } catch (error) {

        console.error(
            "Error loading documents:",
            error
        );


        uploadedFiles.innerHTML = `
            <p class="empty-message">
                Could not load uploaded documents.
            </p>
        `;

    }

}


// ============================================================
// DISPLAY UPLOADED DOCUMENTS
// ============================================================

function displayUploadedDocuments(documents) {

    if (!documents || documents.length === 0) {

        uploadedFiles.innerHTML = `
            <p class="empty-message">
                No documents uploaded yet.
            </p>
        `;

        return;
    }


    uploadedFiles.innerHTML = documents.map(
        function (filename) {

            const extension =
                getFileExtension(filename);


            return `
                <div class="uploaded-file">

                    <div class="uploaded-file-name">
                        📄 ${escapeHtml(filename)}
                    </div>

                    <div class="file-type">
                        ${extension
                            .replace(".", "")
                            .toUpperCase()}
                    </div>

                    <div class="file-status">
                        ✅ Processed
                    </div>

                </div>
            `;

        }
    ).join("");

}


// ============================================================
// ADD PROCESSING RESULT
// ============================================================

function addProcessingResult(data) {

    // Remove empty message

    const emptyMessage =
        processingResults.querySelector(
            ".empty-message"
        );


    if (emptyMessage) {

        processingResults.innerHTML = "";

    }


    const result = document.createElement("div");

    result.className = "processing-result";


    result.innerHTML = `

        <h3>
            📄 ${escapeHtml(
                data.filename || "Uploaded Document"
            )}
        </h3>


        <div class="processing-grid">

            <div class="processing-item">
                <strong>File Type</strong>
                <br>
                ${escapeHtml(
                    data.file_type || "Unknown"
                )}
            </div>


            <div class="processing-item">
                <strong>Characters Extracted</strong>
                <br>
                ${data.characters_extracted ?? 0}
            </div>


            <div class="processing-item">
                <strong>Chunk Size</strong>
                <br>
                ${data.chunk_size ?? 0}
            </div>


            <div class="processing-item">
                <strong>Chunk Overlap</strong>
                <br>
                ${data.overlap ?? 0}
            </div>


            <div class="processing-item">
                <strong>Number of Chunks</strong>
                <br>
                ${data.number_of_chunks ?? 0}
            </div>


            <div class="processing-item">
                <strong>Number of Embeddings</strong>
                <br>
                ${data.number_of_embeddings ?? 0}
            </div>


            <div class="processing-item">
                <strong>ChromaDB</strong>
                <br>
                ${
                    data.chunks_stored_in_chromadb
                        ? "✅ Stored"
                        : "❌ Not Stored"
                }
            </div>


            <div class="processing-item">
                <strong>Embedding Dimension</strong>
                <br>
                ${data.embedding_dimension ?? 768}
            </div>

        </div>

    `;


    // Put newest result at top

    processingResults.prepend(result);

}


// ============================================================
// SEARCH
// ============================================================

searchBtn.addEventListener("click", searchDocuments);


// Press Enter to search

queryInput.addEventListener("keydown", function (event) {

    if (event.key === "Enter") {

        searchDocuments();

    }

});


// ============================================================
// SEARCH DOCUMENTS
// ============================================================

async function searchDocuments() {

    const query =
        queryInput.value.trim();


    if (!query) {

        results.innerHTML = `
            <p class="empty-message">
                Please enter a search query.
            </p>
        `;

        return;
    }


    searchBtn.disabled = true;

    searchBtn.textContent = "Searching...";


    results.innerHTML = `
        <p class="empty-message">
            Searching your documents...
        </p>
    `;


    try {

        const response = await fetch(
            `${API_URL}/search`,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    query: query,
                    n_results: 5
                })
            }
        );


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail || "Search failed."
            );

        }


        displaySearchResults(data.results);


    } catch (error) {

        console.error(
            "Search error:",
            error
        );


        results.innerHTML = `
            <p class="empty-message">
                ❌ Search failed:
                ${escapeHtml(error.message)}
            </p>
        `;

    }


    searchBtn.disabled = false;

    searchBtn.textContent = "Search";

}


// ============================================================
// DISPLAY SEARCH RESULTS
// ============================================================

function displaySearchResults(searchResults) {

    if (
        !searchResults ||
        searchResults.length === 0
    ) {

        results.innerHTML = `
            <p class="empty-message">
                No relevant results found.
            </p>
        `;

        return;
    }


    results.innerHTML = searchResults.map(
        function (result, index) {

            return `

                <div class="result-item">

                    <h3>
                        Result ${index + 1}
                    </h3>


                    <div class="result-text">

                        ${escapeHtml(
                            result.text || ""
                        )}

                    </div>


                    <div class="result-meta">

                        <strong>Source:</strong>
                        ${escapeHtml(
                            result.source || "Unknown"
                        )}

                        <br>

                        <strong>Chunk:</strong>
                        ${result.chunk_number ?? "N/A"}

                        <br>

                        <strong>Score:</strong>
                        ${
                            result.score !== undefined
                                ? Number(result.score).toFixed(4)
                                : "N/A"
                        }

                        <br>

                        <strong>Distance:</strong>
                        ${
                            result.distance !== undefined
                                ? Number(result.distance).toFixed(4)
                                : "N/A"
                        }

                    </div>

                </div>

            `;

        }
    ).join("");

}


// ============================================================
// HELPER: FILE EXTENSION
// ============================================================

function getFileExtension(filename) {

    const lastDot =
        filename.lastIndexOf(".");


    if (lastDot === -1) {

        return "";

    }


    return filename
        .substring(lastDot)
        .toLowerCase();

}


// ============================================================
// HELPER: FILE SIZE
// ============================================================

function formatFileSize(bytes) {

    if (bytes === 0) {

        return "0 Bytes";

    }


    const sizes = [
        "Bytes",
        "KB",
        "MB",
        "GB"
    ];


    const i =
        Math.floor(
            Math.log(bytes) /
            Math.log(1024)
        );


    return (
        parseFloat(
            (
                bytes /
                Math.pow(1024, i)
            ).toFixed(2)
        )
        + " "
        + sizes[i]
    );

}


// ============================================================
// HELPER: ESCAPE HTML
// ============================================================

function escapeHtml(value) {

    if (value === null ||
        value === undefined) {

        return "";

    }


    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


// ============================================================
// LOAD DOCUMENTS WHEN PAGE OPENS
// ============================================================

loadUploadedDocuments();