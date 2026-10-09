import re
import math

from collections import Counter


# ============================================================
# BM25 KEYWORD SEARCH SERVICE
# ============================================================
#
# Provides keyword-based document retrieval using the BM25
# (Okapi BM25) scoring algorithm. This complements vector
# similarity search to enable hybrid retrieval.
# ============================================================


# ============================================================
# TOKENIZER
# ============================================================


# Common English stop words to filter out during tokenization

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "and",
    "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more",
    "most", "other", "some", "such", "no", "only", "own", "same",
    "than", "too", "very", "just", "because", "about", "between",
    "if", "then", "else", "when", "where", "how", "what", "which",
    "who", "whom", "this", "that", "these", "those", "i", "me",
    "my", "we", "our", "you", "your", "he", "him", "his", "she",
    "her", "it", "its", "they", "them", "their",
}


def tokenize(text):
    """
    Tokenizes text into lowercase words, removing
    stop words and short tokens.
    """

    text = text.lower()

    # Extract alphanumeric tokens

    tokens = re.findall(r"\b[a-z0-9]{2,}\b", text)

    # Filter out stop words

    tokens = [t for t in tokens if t not in STOP_WORDS]

    return tokens


# ============================================================
# BM25 INDEX
# ============================================================


class BM25Index:
    """
    In-memory BM25 index for keyword-based document scoring.

    BM25 Parameters:
        k1 = 1.5  (term frequency saturation)
        b  = 0.75 (document length normalization)
    """

    def __init__(self, k1=1.5, b=0.75):

        self.k1 = k1
        self.b = b

        # List of tokenized documents
        self.corpus = []

        # Original document texts (parallel to corpus)
        self.documents = []

        # Document metadata (parallel to corpus)
        self.metadatas = []

        # Document frequency for each term
        self.df = Counter()

        # Average document length
        self.avgdl = 0.0

        # Total number of documents
        self.n_docs = 0

    # --------------------------------------------------------
    # BUILD INDEX
    # --------------------------------------------------------

    def build(self, documents, metadatas=None):
        """
        Builds the BM25 index from a list of document strings.
        """

        self.documents = list(documents)

        self.metadatas = list(metadatas) if metadatas else [
            {} for _ in documents
        ]

        self.corpus = [tokenize(doc) for doc in self.documents]

        self.n_docs = len(self.corpus)

        # Compute document frequencies

        self.df = Counter()

        for tokens in self.corpus:

            unique_tokens = set(tokens)

            for token in unique_tokens:

                self.df[token] += 1

        # Compute average document length

        total_length = sum(len(tokens) for tokens in self.corpus)

        self.avgdl = total_length / self.n_docs if self.n_docs > 0 else 0.0

    # --------------------------------------------------------
    # COMPUTE IDF
    # --------------------------------------------------------

    def _idf(self, term):
        """
        Inverse document frequency with smoothing.
        """

        df = self.df.get(term, 0)

        return math.log(
            (self.n_docs - df + 0.5) / (df + 0.5) + 1.0
        )

    # --------------------------------------------------------
    # SCORE SINGLE DOCUMENT
    # --------------------------------------------------------

    def _score_document(self, query_tokens, doc_index):
        """
        Computes BM25 score for a single document against
        the query tokens.
        """

        doc_tokens = self.corpus[doc_index]

        doc_len = len(doc_tokens)

        tf = Counter(doc_tokens)

        score = 0.0

        for term in query_tokens:

            if term not in tf:
                continue

            term_freq = tf[term]

            idf = self._idf(term)

            # BM25 formula

            numerator = term_freq * (self.k1 + 1)

            denominator = term_freq + self.k1 * (
                1 - self.b + self.b * (doc_len / self.avgdl)
            )

            score += idf * (numerator / denominator)

        return score

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    def search(self, query, n_results=5):
        """
        Searches the index and returns the top n_results
        documents ranked by BM25 score.

        Returns a list of dicts with:
            text, bm25_score, source, chunk_number
        """

        if self.n_docs == 0:
            return []

        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        # Score all documents

        scores = []

        for i in range(self.n_docs):

            score = self._score_document(query_tokens, i)

            if score > 0:

                scores.append((i, score))

        # Sort by score descending

        scores.sort(key=lambda x: x[1], reverse=True)

        # Take top n

        top_results = scores[:n_results]

        results = []

        for doc_index, bm25_score in top_results:

            metadata = self.metadatas[doc_index] if doc_index < len(self.metadatas) else {}

            results.append({
                "text": self.documents[doc_index],
                "bm25_score": float(bm25_score),
                "source": metadata.get("source", "Unknown"),
                "chunk_number": metadata.get("chunk_number", "Unknown"),
            })

        return results


# ============================================================
# GLOBAL INDEX INSTANCE
# ============================================================


_bm25_index = BM25Index()

# Flag to track whether the index needs rebuilding

_index_dirty = True


# ============================================================
# MARK INDEX AS DIRTY
# ============================================================


def mark_index_dirty():
    """
    Marks the BM25 index as needing a rebuild.
    Called after new documents are uploaded.
    """

    global _index_dirty

    _index_dirty = True


# ============================================================
# BUILD INDEX FROM CHROMADB
# ============================================================


def rebuild_index_from_collection(collection):
    """
    Rebuilds the BM25 index from all documents
    stored in ChromaDB.
    """

    global _bm25_index, _index_dirty

    result = collection.get(include=["documents", "metadatas"])

    documents = result.get("documents", [])

    metadatas = result.get("metadatas", [])

    if not documents:

        _bm25_index = BM25Index()

        _index_dirty = False

        return

    _bm25_index.build(documents, metadatas)

    _index_dirty = False


# ============================================================
# KEYWORD SEARCH
# ============================================================


def keyword_search(query, collection, n_results=5):
    """
    Performs BM25 keyword search across all documents
    in the collection. Rebuilds the index if needed.
    """

    global _index_dirty

    if _index_dirty:

        rebuild_index_from_collection(collection)

    return _bm25_index.search(query, n_results)
