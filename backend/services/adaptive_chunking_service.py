import re
import math


# ============================================================
# ADAPTIVE CHUNKING SERVICE
# ============================================================
#
# Splits documents using semantic boundaries (sentences and
# paragraphs) instead of fixed character counts. Dynamically
# adjusts chunk sizes based on document characteristics.
# ============================================================


# ============================================================
# SENTENCE SPLITTER
# ============================================================


def split_into_sentences(text):
    """
    Splits text into sentences using punctuation and
    newline boundaries.

    Handles common abbreviations (Mr., Dr., etc.)
    to avoid false splits.
    """

    # Protect common abbreviations from being split

    abbreviations = [
        "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.",
        "vs.", "etc.", "e.g.", "i.e.", "Fig.", "fig.",
        "Vol.", "vol.", "No.", "no.", "Dept.", "dept.",
        "Inc.", "Ltd.", "Corp.", "Co.",
    ]

    protected = text

    placeholders = {}

    for i, abbr in enumerate(abbreviations):

        placeholder = f"__ABBR{i}__"

        placeholders[placeholder] = abbr

        protected = protected.replace(abbr, placeholder)

    # Split on sentence-ending punctuation followed by
    # whitespace or end of string

    raw_sentences = re.split(
        r"(?<=[.!?])\s+|\n{2,}",
        protected
    )

    # Restore abbreviations

    sentences = []

    for sentence in raw_sentences:

        restored = sentence

        for placeholder, original in placeholders.items():

            restored = restored.replace(placeholder, original)

        restored = restored.strip()

        if restored:

            sentences.append(restored)

    return sentences


# ============================================================
# PARAGRAPH SPLITTER
# ============================================================


def split_into_paragraphs(text):
    """
    Splits text on double-newlines to detect paragraph
    boundaries.
    """

    paragraphs = re.split(r"\n\s*\n", text)

    return [p.strip() for p in paragraphs if p.strip()]


# ============================================================
# COMPUTE ADAPTIVE TARGET SIZE
# ============================================================


def compute_target_chunk_size(
    text,
    min_size=300,
    max_size=1500,
    default_size=800
):
    """
    Dynamically determines the ideal chunk size based on
    document characteristics:

    - Short documents  (< 2000 chars)  → smaller chunks
    - Medium documents (2000–20000)    → default size
    - Long documents   (> 20000 chars) → larger chunks

    Also adjusts based on content density:
    - Dense text (few paragraphs) → larger chunks
    - Sparse text (many paragraphs) → smaller chunks
    """

    text_length = len(text)

    paragraphs = split_into_paragraphs(text)

    n_paragraphs = len(paragraphs)

    # --------------------------------------------------------
    # Base size from document length
    # --------------------------------------------------------

    if text_length < 2000:

        base_size = min_size

    elif text_length > 20000:

        base_size = max_size

    else:

        # Linear interpolation between min and max

        ratio = (text_length - 2000) / (20000 - 2000)

        base_size = int(min_size + ratio * (max_size - min_size))

    # --------------------------------------------------------
    # Adjust for content density
    # --------------------------------------------------------

    if n_paragraphs > 0:

        avg_paragraph_length = text_length / n_paragraphs

        if avg_paragraph_length < 200:

            # Many short paragraphs → reduce chunk size

            density_factor = 0.8

        elif avg_paragraph_length > 1000:

            # Few long paragraphs → increase chunk size

            density_factor = 1.2

        else:

            density_factor = 1.0

    else:

        density_factor = 1.0

    target_size = int(base_size * density_factor)

    # Clamp to valid range

    target_size = max(min_size, min(max_size, target_size))

    return target_size


# ============================================================
# CREATE ADAPTIVE CHUNKS
# ============================================================


def create_adaptive_chunks(
    text,
    target_size=None,
    overlap_sentences=1,
    min_chunk_size=100,
):
    """
    Creates chunks using sentence-aware boundaries.

    Parameters:
        text:              The full document text.
        target_size:       Target chunk size in characters.
                           If None, computed automatically.
        overlap_sentences: Number of sentences to overlap
                           between adjacent chunks.
        min_chunk_size:    Minimum chunk size in characters.

    Returns:
        A list of text chunks.
    """

    # Clean up whitespace

    text = re.sub(r"[ \t]+", " ", text)

    text = text.strip()

    if not text:
        return []

    # Compute target size if not provided

    if target_size is None:

        target_size = compute_target_chunk_size(text)

    # --------------------------------------------------------
    # Split into sentences
    # --------------------------------------------------------

    sentences = split_into_sentences(text)

    if not sentences:
        return [text] if len(text) >= min_chunk_size else []

    # --------------------------------------------------------
    # Group sentences into chunks
    # --------------------------------------------------------

    chunks = []

    current_sentences = []

    current_length = 0

    for sentence in sentences:

        sentence_length = len(sentence)

        # If adding this sentence exceeds target and we
        # already have content, finalize the current chunk

        if (
            current_length + sentence_length > target_size
            and current_sentences
        ):

            chunk_text = " ".join(current_sentences)

            if len(chunk_text) >= min_chunk_size:

                chunks.append(chunk_text)

            # Overlap: carry the last N sentences forward

            if overlap_sentences > 0 and len(current_sentences) > overlap_sentences:

                current_sentences = current_sentences[-overlap_sentences:]

                current_length = sum(len(s) for s in current_sentences)

            else:

                current_sentences = []

                current_length = 0

        current_sentences.append(sentence)

        current_length += sentence_length

    # --------------------------------------------------------
    # Handle remaining sentences
    # --------------------------------------------------------

    if current_sentences:

        chunk_text = " ".join(current_sentences)

        if len(chunk_text) >= min_chunk_size:

            chunks.append(chunk_text)

        elif chunks:

            # Merge short remainder into last chunk

            chunks[-1] = chunks[-1] + " " + chunk_text

    # --------------------------------------------------------
    # Handle edge case: no chunks produced
    # --------------------------------------------------------

    if not chunks and text:

        chunks = [text]

    return chunks


# ============================================================
# GET CHUNKING STATS
# ============================================================


def get_chunking_stats(chunks):
    """
    Returns statistics about the generated chunks.
    Useful for monitoring adaptive chunking performance.
    """

    if not chunks:

        return {
            "num_chunks": 0,
            "avg_chunk_size": 0,
            "min_chunk_size": 0,
            "max_chunk_size": 0,
            "total_characters": 0,
        }

    sizes = [len(chunk) for chunk in chunks]

    return {
        "num_chunks": len(chunks),
        "avg_chunk_size": int(sum(sizes) / len(sizes)),
        "min_chunk_size": min(sizes),
        "max_chunk_size": max(sizes),
        "total_characters": sum(sizes),
    }
