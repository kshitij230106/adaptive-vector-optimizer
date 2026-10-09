// ============================================================
// ADAPTIVE VECTOR OPTIMIZER — FRONTEND
// ============================================================


// API URL

const API_URL = "http://127.0.0.1:8000";


// Allowed file extensions

const allowedExtensions = [
    ".pdf",
    ".doc",
    ".docx",
    ".pptx",
    ".txt",
    ".md"
];


// ============================================================
// DOM ELEMENTS
// ============================================================

const fileInput        = document.getElementById("fileInput");
const dropZone         = document.getElementById("dropZone");
const selectedFiles    = document.getElementById("selectedFiles");
const chunkSizeInput   = document.getElementById("chunkSize");
const overlapInput     = document.getElementById("overlap");
const uploadBtn        = document.getElementById("uploadBtn");
const uploadStatus     = document.getElementById("uploadStatus");
const uploadedFiles    = document.getElementById("uploadedFiles");
const processingResults = document.getElementById("processingResults");
const queryInput       = document.getElementById("queryInput");
const searchBtn        = document.getElementById("searchBtn");
const resultsContainer = document.getElementById("results");

// Chunking mode
const chunkingModeToggle  = document.getElementById("chunkingModeToggle");
const fixedChunkSettings  = document.getElementById("fixedChunkSettings");

// Dedup at ingest
const enableDedupCheckbox = document.getElementById("enableDedup");
const dedupThresholdGroup = document.getElementById("dedupThresholdGroup");
const dedupThresholdInput = document.getElementById("dedupThreshold");
const dedupThresholdValue = document.getElementById("dedupThresholdValue");

// Search settings
const searchModeToggle     = document.getElementById("searchModeToggle");
const alphaGroup           = document.getElementById("alphaGroup");
const alphaSlider          = document.getElementById("alphaSlider");
const alphaValue           = document.getElementById("alphaValue");
const nResultsSelect       = document.getElementById("nResults");
const optimizeQueryCheckbox = document.getElementById("optimizeQuery");
const deduplicateCheckbox  = document.getElementById("deduplicateResults");

// Cache
const refreshCacheBtn = document.getElementById("refreshCacheBtn");
const clearCacheBtn   = document.getElementById("clearCacheBtn");
const cacheStatsEl    = document.getElementById("cacheStats");


// ============================================================
// STATE
// ============================================================

let currentChunkingMode = "adaptive";
let currentSearchMode   = "hybrid";


// ============================================================
// INITIALISE
// ============================================================

console.log("Frontend loaded successfully.");

loadUploadedDocuments();
loadCacheStats();


// ============================================================
// DROP ZONE — DRAG & DROP
// ============================================================

dropZone.addEventListener("click", function () {
    fileInput.click();
});

dropZone.addEventListener("dragover", function (e) {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", function () {
    dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", function (e) {
    e.preventDefault();
    dropZone.classList.remove("drag-over");

    if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        showSelectedFile(e.dataTransfer.files[0]);
    }
});


// ============================================================
// FILE SELECTION
// ============================================================

fileInput.addEventListener("change", function () {

    const file = fileInput.files[0];

    if (!file) {
        selectedFiles.innerHTML = "";
        return;
    }

    showSelectedFile(file);
});


function showSelectedFile(file) {

    selectedFiles.innerHTML = `
        <div class="selected-file">
            <span class="file-icon">📄</span>
            <div class="file-info">
                <div class="file-name">${escapeHtml(file.name)}</div>
                <div class="file-meta">
                    ${getFileExtension(file.name).replace(".", "").toUpperCase()}
                    &middot;
                    ${formatFileSize(file.size)}
                </div>
            </div>
            <button class="remove-file" title="Remove file" type="button">✕</button>
        </div>
    `;

    const removeBtn = selectedFiles.querySelector(".remove-file");

    if (removeBtn) {
        removeBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            fileInput.value = "";
            selectedFiles.innerHTML = "";
        });
    }
}


// ============================================================
// CHUNKING MODE TOGGLE
// ============================================================

initToggleGroup(chunkingModeToggle, function (value) {

    currentChunkingMode = value;

    if (value === "fixed") {
        fixedChunkSettings.style.display = "grid";
    } else {
        fixedChunkSettings.style.display = "none";
    }
});


// ============================================================
// DEDUP TOGGLE — SHOW/HIDE THRESHOLD
// ============================================================

enableDedupCheckbox.addEventListener("change", function () {

    if (enableDedupCheckbox.checked) {
        dedupThresholdGroup.style.display = "block";
    } else {
        dedupThresholdGroup.style.display = "none";
    }
});


// ============================================================
// DEDUP THRESHOLD SLIDER — LIVE VALUE
// ============================================================

dedupThresholdInput.addEventListener("input", function () {
    dedupThresholdValue.textContent = parseFloat(dedupThresholdInput.value).toFixed(2);
});


// ============================================================
// SEARCH MODE TOGGLE
// ============================================================

initToggleGroup(searchModeToggle, function (value) {

    currentSearchMode = value;

    // Show alpha slider only for hybrid
    if (value === "hybrid") {
        alphaGroup.style.display = "block";
    } else {
        alphaGroup.style.display = "none";
    }
});


// ============================================================
// ALPHA SLIDER — LIVE VALUE
// ============================================================

alphaSlider.addEventListener("input", function () {
    alphaValue.textContent = parseFloat(alphaSlider.value).toFixed(2);
});


// ============================================================
// UPLOAD DOCUMENT
// ============================================================

uploadBtn.addEventListener("click", async function () {

    const file = fileInput.files[0];


    // Check file

    if (!file) {
        setStatus(uploadStatus, "Please select a document first.", "");
        return;
    }


    // Check extension

    const extension = getFileExtension(file.name);

    if (!allowedExtensions.includes(extension)) {
        setStatus(uploadStatus, "Unsupported file type.", "error");
        return;
    }


    // Build query params

    const params = new URLSearchParams();

    params.set("chunking_mode", currentChunkingMode);
    params.set("enable_dedup", enableDedupCheckbox.checked);
    params.set("similarity_threshold", dedupThresholdInput.value);

    if (currentChunkingMode === "fixed") {

        const chunkSize = parseInt(chunkSizeInput.value);
        const overlap   = parseInt(overlapInput.value);

        if (isNaN(chunkSize) || chunkSize < 100) {
            setStatus(uploadStatus, "Chunk size must be at least 100.", "error");
            return;
        }

        if (isNaN(overlap) || overlap < 0) {
            setStatus(uploadStatus, "Chunk overlap cannot be negative.", "error");
            return;
        }

        if (overlap >= chunkSize) {
            setStatus(uploadStatus, "Chunk overlap must be smaller than chunk size.", "error");
            return;
        }

        params.set("chunk_size", chunkSize);
        params.set("overlap", overlap);
    }


    // Disable button

    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner"></span> Processing…';

    setStatus(
        uploadStatus,
        `Uploading ${escapeHtml(file.name)}…`,
        "processing"
    );


    try {

        const formData = new FormData();
        formData.append("file", file);


        const response = await fetch(
            `${API_URL}/upload?${params.toString()}`,
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();


        if (!response.ok) {
            throw new Error(data.detail || "Upload failed.");
        }


        setStatus(
            uploadStatus,
            `✅ ${escapeHtml(file.name)} uploaded and processed successfully.`,
            "success"
        );


        // Clear selected file
        fileInput.value = "";
        selectedFiles.innerHTML = "";

        // Refresh lists
        await loadUploadedDocuments();
        loadCacheStats();

        // Show processing result
        addProcessingResult(data);


    } catch (error) {

        console.error("Upload error:", error);

        setStatus(
            uploadStatus,
            `❌ Upload failed: ${escapeHtml(error.message)}`,
            "error"
        );
    }


    // Re-enable button

    uploadBtn.disabled = false;
    uploadBtn.innerHTML = '<span class="btn-icon">🚀</span> Upload &amp; Process';

});


// ============================================================
// LOAD UPLOADED DOCUMENTS
// ============================================================

async function loadUploadedDocuments() {

    try {

        const response = await fetch(`${API_URL}/documents`);

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not load documents.");
        }

        displayUploadedDocuments(data.documents);


    } catch (error) {

        console.error("Error loading documents:", error);

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

    uploadedFiles.innerHTML = documents.map(function (filename) {

        const ext = getFileExtension(filename)
            .replace(".", "")
            .toUpperCase();

        return `
            <div class="uploaded-file">
                <span class="uploaded-file-icon">📄</span>
                <div class="uploaded-file-name">
                    ${escapeHtml(filename)}
                </div>
                <span class="file-type">${ext}</span>
                <span class="file-status">✅ Processed</span>
            </div>
        `;

    }).join("");
}


// ============================================================
// ADD PROCESSING RESULT
// ============================================================

function addProcessingResult(data) {

    // Remove empty message

    const emptyMessage =
        processingResults.querySelector(".empty-message");

    if (emptyMessage) {
        processingResults.innerHTML = "";
    }


    const result = document.createElement("div");
    result.className = "processing-result";


    // Build main grid

    let gridHtml = `
        <div class="processing-grid">

            <div class="processing-item">
                <strong>File Type</strong>
                <span class="value">${escapeHtml(data.file_type || "Unknown")}</span>
            </div>

            <div class="processing-item">
                <strong>Characters</strong>
                <span class="value">${(data.characters_extracted ?? 0).toLocaleString()}</span>
            </div>

            <div class="processing-item">
                <strong>Chunking Mode</strong>
                <span class="value">${escapeHtml(data.chunking_mode || "fixed")}</span>
            </div>

            <div class="processing-item">
                <strong>Chunk Size</strong>
                <span class="value">${data.chunk_size ?? "auto"}</span>
            </div>

            <div class="processing-item">
                <strong>Overlap</strong>
                <span class="value">${data.overlap ?? "adaptive"}</span>
            </div>

            <div class="processing-item">
                <strong>Chunks</strong>
                <span class="value">${data.number_of_chunks ?? 0}</span>
            </div>

            <div class="processing-item">
                <strong>Embeddings</strong>
                <span class="value">${data.number_of_embeddings ?? 0}</span>
            </div>

            <div class="processing-item">
                <strong>Dimension</strong>
                <span class="value">${data.embedding_dimension ?? 768}</span>
            </div>

            <div class="processing-item">
                <strong>ChromaDB</strong>
                <span class="value">${
                    data.chunks_stored_in_chromadb
                        ? "✅ Stored"
                        : "❌ Not Stored"
                }</span>
            </div>

            <div class="processing-item">
                <strong>Time</strong>
                <span class="value">${data.processing_time_seconds ?? "—"}s</span>
            </div>

        </div>
    `;


    // Chunking stats (adaptive mode)

    if (data.chunking_stats) {

        const cs = data.chunking_stats;

        gridHtml += `
            <div class="chunking-stats">
                <h4>📐 Adaptive Chunking Stats</h4>
                <div class="processing-grid">
                    <div class="processing-item">
                        <strong>Total Chunks</strong>
                        <span class="value">${cs.total_chunks ?? "—"}</span>
                    </div>
                    <div class="processing-item">
                        <strong>Avg Length</strong>
                        <span class="value">${cs.avg_chunk_length ?? "—"}</span>
                    </div>
                    <div class="processing-item">
                        <strong>Min Length</strong>
                        <span class="value">${cs.min_chunk_length ?? "—"}</span>
                    </div>
                    <div class="processing-item">
                        <strong>Max Length</strong>
                        <span class="value">${cs.max_chunk_length ?? "—"}</span>
                    </div>
                </div>
            </div>
        `;
    }


    // Dedup stats

    if (data.dedup_stats) {

        const ds = data.dedup_stats;

        gridHtml += `
            <div class="dedup-stats">
                <h4>🧹 Deduplication Stats</h4>
                <div class="processing-grid">
                    <div class="processing-item">
                        <strong>Original</strong>
                        <span class="value">${ds.original_count ?? "—"}</span>
                    </div>
                    <div class="processing-item">
                        <strong>Exact Dupes</strong>
                        <span class="value">${ds.exact_duplicates_removed ?? 0}</span>
                    </div>
                    <div class="processing-item">
                        <strong>Near Dupes</strong>
                        <span class="value">${ds.near_duplicates_removed ?? 0}</span>
                    </div>
                    <div class="processing-item">
                        <strong>Final</strong>
                        <span class="value">${ds.final_count ?? "—"}</span>
                    </div>
                    <div class="processing-item">
                        <strong>Total Removed</strong>
                        <span class="value">${ds.total_removed ?? 0}</span>
                    </div>
                    <div class="processing-item">
                        <strong>Threshold</strong>
                        <span class="value">${ds.similarity_threshold ?? "—"}</span>
                    </div>
                </div>
            </div>
        `;
    }


    result.innerHTML = `
        <h3>📄 ${escapeHtml(data.filename || "Uploaded Document")}</h3>
        ${gridHtml}
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

    const query = queryInput.value.trim();


    if (!query) {

        resultsContainer.innerHTML = `
            <p class="empty-message">
                Please enter a search query.
            </p>
        `;

        return;
    }


    searchBtn.disabled = true;
    searchBtn.innerHTML = '<span class="spinner"></span> Searching…';


    resultsContainer.innerHTML = `
        <p class="empty-message">
            <span class="spinner"></span> Searching your documents…
        </p>
    `;


    try {

        const requestBody = {
            query: query,
            n_results: parseInt(nResultsSelect.value),
            search_mode: currentSearchMode,
            alpha: parseFloat(alphaSlider.value),
            optimize_query: optimizeQueryCheckbox.checked,
            deduplicate: deduplicateCheckbox.checked
        };


        const response = await fetch(
            `${API_URL}/search`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(requestBody)
            }
        );

        const data = await response.json();


        if (!response.ok) {
            throw new Error(data.detail || "Search failed.");
        }


        displaySearchResults(data);

        // Refresh cache stats after search
        loadCacheStats();


    } catch (error) {

        console.error("Search error:", error);

        resultsContainer.innerHTML = `
            <p class="empty-message">
                ❌ Search failed: ${escapeHtml(error.message)}
            </p>
        `;
    }


    searchBtn.disabled = false;
    searchBtn.innerHTML = '<span class="btn-icon">🔍</span> Search';
}


// ============================================================
// DISPLAY SEARCH RESULTS
// ============================================================

function displaySearchResults(data) {

    const searchResults = data.results;

    if (!searchResults || searchResults.length === 0) {

        resultsContainer.innerHTML = `
            <p class="empty-message">
                No relevant results found.
            </p>
        `;

        return;
    }


    // ---- META HEADER ----

    let metaHtml = `<div class="search-meta">`;

    metaHtml += `<span><strong>${data.result_count}</strong> results</span>`;

    metaHtml += `<span><strong>${data.response_time_ms}</strong>ms</span>`;

    metaHtml += `<span class="meta-badge mode">${escapeHtml(data.search_mode)}</span>`;

    if (data.cache_hit) {
        metaHtml += `<span class="meta-badge cached">⚡ cached</span>`;
    }

    if (data.query_optimization) {

        const opt = data.query_optimization;

        if (opt.key_terms && opt.key_terms.length > 0) {

            metaHtml += `<div class="key-terms">Key terms: `;

            metaHtml += opt.key_terms.map(function (term) {
                return `<span class="term">${escapeHtml(term)}</span>`;
            }).join("");

            metaHtml += `</div>`;
        }

        if (opt.optimized && opt.optimized !== opt.original) {
            metaHtml += `<div class="key-terms">Optimized: "${escapeHtml(opt.optimized)}"</div>`;
        }
    }

    metaHtml += `</div>`;


    // ---- RESULT ITEMS ----

    const resultsHtml = searchResults.map(function (result, index) {

        // Scores
        let scoresHtml = "";

        if (result.score !== undefined) {
            scoresHtml += `
                <span class="score-pill">
                    Score <strong>${Number(result.score).toFixed(4)}</strong>
                </span>`;
        }

        if (result.vector_score !== undefined) {
            scoresHtml += `
                <span class="score-pill">
                    Vector <strong>${Number(result.vector_score).toFixed(4)}</strong>
                </span>`;
        }

        if (result.bm25_score !== undefined) {
            scoresHtml += `
                <span class="score-pill">
                    BM25 <strong>${Number(result.bm25_score).toFixed(4)}</strong>
                </span>`;
        }

        if (result.distance !== undefined) {
            scoresHtml += `
                <span class="score-pill">
                    Dist <strong>${Number(result.distance).toFixed(4)}</strong>
                </span>`;
        }


        return `
            <div class="result-item" style="animation-delay: ${index * 0.05}s">

                <div class="result-header">
                    <span class="result-rank">${index + 1}</span>
                    <span class="result-source">
                        ${escapeHtml(result.source || "Unknown")}
                        ${result.chunk_number !== undefined
                            ? " · chunk " + result.chunk_number
                            : ""}
                    </span>
                </div>

                <div class="result-text">
                    ${escapeHtml(result.text || "")}
                </div>

                <div class="result-scores">
                    ${scoresHtml}
                </div>

            </div>
        `;

    }).join("");


    resultsContainer.innerHTML = metaHtml + resultsHtml;
}


// ============================================================
// CACHE STATS
// ============================================================

async function loadCacheStats() {

    try {

        const response = await fetch(`${API_URL}/cache/stats`);

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not load cache stats.");
        }

        displayCacheStats(data);

    } catch (error) {

        console.error("Cache stats error:", error);

        cacheStatsEl.innerHTML = `
            <p class="empty-message">
                Could not load cache stats.
            </p>
        `;
    }
}

function displayCacheStats(stats) {

    cacheStatsEl.innerHTML = `
        <div class="cache-stat-item">
            <div class="stat-value">${stats.cache_size ?? 0}</div>
            <div class="stat-label">Entries</div>
        </div>
        <div class="cache-stat-item">
            <div class="stat-value">${stats.hits ?? 0}</div>
            <div class="stat-label">Hits</div>
        </div>
        <div class="cache-stat-item">
            <div class="stat-value">${stats.misses ?? 0}</div>
            <div class="stat-label">Misses</div>
        </div>
        <div class="cache-stat-item">
            <div class="stat-value">${stats.hit_rate_percent ?? 0}%</div>
            <div class="stat-label">Hit Rate</div>
        </div>
        <div class="cache-stat-item">
            <div class="stat-value">${stats.evictions ?? 0}</div>
            <div class="stat-label">Evictions</div>
        </div>
        <div class="cache-stat-item">
            <div class="stat-value">${stats.max_size ?? 0}</div>
            <div class="stat-label">Max Size</div>
        </div>
    `;
}


// Refresh cache

refreshCacheBtn.addEventListener("click", function () {
    loadCacheStats();
});


// Clear cache

clearCacheBtn.addEventListener("click", async function () {

    try {

        const response = await fetch(`${API_URL}/cache/clear`, {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not clear cache.");
        }

        loadCacheStats();

    } catch (error) {

        console.error("Clear cache error:", error);
    }
});


// ============================================================
// TOGGLE GROUP HELPER
// ============================================================

function initToggleGroup(container, onChangeCallback) {

    const buttons = container.querySelectorAll(".toggle-btn");

    buttons.forEach(function (btn) {

        btn.addEventListener("click", function () {

            // Deactivate all
            buttons.forEach(function (b) {
                b.classList.remove("active");
                b.setAttribute("aria-checked", "false");
            });

            // Activate clicked
            btn.classList.add("active");
            btn.setAttribute("aria-checked", "true");

            // Callback with value
            onChangeCallback(btn.dataset.value);
        });
    });
}


// ============================================================
// STATUS HELPER
// ============================================================

function setStatus(element, message, type) {

    const textEl = element.querySelector(".status-text");

    if (textEl) {
        textEl.innerHTML = message;
    } else {
        element.innerHTML = `<span class="status-text">${message}</span>`;
    }

    // Remove all state classes
    element.classList.remove("success", "error", "processing");

    if (type) {
        element.classList.add(type);
    }
}


// ============================================================
// HELPER: FILE EXTENSION
// ============================================================

function getFileExtension(filename) {

    const lastDot = filename.lastIndexOf(".");

    if (lastDot === -1) {
        return "";
    }

    return filename.substring(lastDot).toLowerCase();
}


// ============================================================
// HELPER: FILE SIZE
// ============================================================

function formatFileSize(bytes) {

    if (bytes === 0) {
        return "0 Bytes";
    }

    const sizes = ["Bytes", "KB", "MB", "GB"];

    const i = Math.floor(
        Math.log(bytes) / Math.log(1024)
    );

    return (
        parseFloat(
            (bytes / Math.pow(1024, i)).toFixed(2)
        )
        + " "
        + sizes[i]
    );
}


// ============================================================
// HELPER: ESCAPE HTML
// ============================================================

function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}