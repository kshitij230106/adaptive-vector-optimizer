import re


# ============================================================
# QUERY OPTIMIZER SERVICE
# ============================================================
#
# Pre-processes user queries before retrieval to improve
# search quality. Includes term extraction, abbreviation
# expansion, query rephrasing, and multi-query merging.
# ============================================================


# ============================================================
# STOP WORDS
# ============================================================


STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "and", "but", "or", "not", "so", "if", "then",
    "when", "where", "how", "what", "which", "who", "whom",
    "this", "that", "these", "those", "i", "me", "my", "we",
    "our", "you", "your", "he", "him", "she", "her", "it",
    "they", "them", "their", "tell", "about", "please",
    "explain", "describe", "give", "show", "list",
}


# ============================================================
# COMMON ABBREVIATIONS
# ============================================================


ABBREVIATION_MAP = {
    "db": "database",
    "sql": "structured query language",
    "api": "application programming interface",
    "ui": "user interface",
    "ux": "user experience",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "os": "operating system",
    "cpu": "central processing unit",
    "gpu": "graphics processing unit",
    "ram": "random access memory",
    "ssd": "solid state drive",
    "hdd": "hard disk drive",
    "http": "hypertext transfer protocol",
    "html": "hypertext markup language",
    "css": "cascading style sheets",
    "js": "javascript",
    "csv": "comma separated values",
    "pdf": "portable document format",
    "oop": "object oriented programming",
    "ide": "integrated development environment",
    "cli": "command line interface",
    "devops": "development operations",
    "ci": "continuous integration",
    "cd": "continuous deployment",
    "vpc": "virtual private cloud",
    "dns": "domain name system",
    "tcp": "transmission control protocol",
    "ip": "internet protocol",
    "auth": "authentication",
    "config": "configuration",
    "env": "environment",
    "repo": "repository",
    "pkg": "package",
    "dept": "department",
    "mgmt": "management",
    "emp": "employee",
    "org": "organization",
    "govt": "government",
    "info": "information",
    "tech": "technology",
    "admin": "administrator",
}


# ============================================================
# EXTRACT KEY TERMS
# ============================================================


def extract_key_terms(query):
    """
    Extracts meaningful terms from the query by
    removing stop words and noise.
    """

    query_lower = query.lower()

    # Extract alphanumeric tokens

    tokens = re.findall(r"\b[a-z0-9_]{2,}\b", query_lower)

    # Remove stop words

    key_terms = [t for t in tokens if t not in STOP_WORDS]

    return key_terms


# ============================================================
# EXPAND ABBREVIATIONS
# ============================================================


def expand_abbreviations(query):
    """
    Expands known abbreviations found in the query.
    The original abbreviation is preserved alongside
    the expansion to improve recall.
    """

    query_lower = query.lower()

    tokens = re.findall(r"\b[a-z0-9_]+\b", query_lower)

    expansions = []

    for token in tokens:

        if token in ABBREVIATION_MAP:

            expansions.append(ABBREVIATION_MAP[token])

    if expansions:

        return query + " " + " ".join(expansions)

    return query


# ============================================================
# REPHRASE AS STATEMENT
# ============================================================


def rephrase_as_statement(query):
    """
    Converts question-form queries into statement form
    to broaden retrieval. For example:

    "What is machine learning?" → "machine learning"
    "How does TCP work?"       → "TCP work"
    """

    query_stripped = query.strip().rstrip("?").strip()

    # Remove common question prefixes

    question_prefixes = [
        r"^what\s+(?:is|are|was|were)\s+",
        r"^what\s+does\s+",
        r"^what\s+do\s+",
        r"^how\s+(?:does|do|did|can|could|would|is|are)\s+",
        r"^how\s+to\s+",
        r"^who\s+(?:is|are|was|were)\s+",
        r"^where\s+(?:is|are|was|were)\s+",
        r"^when\s+(?:is|are|was|were|did|does|do)\s+",
        r"^why\s+(?:is|are|was|were|did|does|do)\s+",
        r"^can\s+you\s+(?:tell\s+me\s+(?:about\s+)?|explain\s+|describe\s+)?",
        r"^(?:tell\s+me\s+about\s+)",
        r"^(?:explain\s+(?:what\s+)?)",
        r"^(?:describe\s+)",
        r"^(?:define\s+)",
    ]

    result = query_stripped

    for prefix in question_prefixes:

        result = re.sub(prefix, "", result, flags=re.IGNORECASE)

    return result.strip()


# ============================================================
# GENERATE QUERY VARIANTS
# ============================================================


def generate_query_variants(query, max_variants=3):
    """
    Generates alternative phrasings of the query to
    improve retrieval coverage.

    Returns a list of query strings (including the original).
    """

    variants = [query.strip()]

    # Variant 1: Key terms only

    key_terms = extract_key_terms(query)

    if key_terms:

        terms_query = " ".join(key_terms)

        if terms_query != query.strip().lower():

            variants.append(terms_query)

    # Variant 2: Abbreviation expansion

    expanded = expand_abbreviations(query)

    if expanded != query:

        variants.append(expanded)

    # Variant 3: Statement rephrasing

    statement = rephrase_as_statement(query)

    if statement and statement.lower() != query.strip().lower():

        variants.append(statement)

    # Deduplicate while preserving order

    seen = set()

    unique_variants = []

    for v in variants:

        v_normalized = v.strip().lower()

        if v_normalized not in seen and v_normalized:

            seen.add(v_normalized)

            unique_variants.append(v.strip())

    return unique_variants[:max_variants]


# ============================================================
# OPTIMIZE QUERY
# ============================================================


def optimize_query(query):
    """
    Full query optimization pipeline.

    Returns a dict containing:
        original:  The original query
        optimized: The best optimized version
        variants:  All generated query variants
        key_terms: Extracted key terms
    """

    original = query.strip()

    # Extract key terms

    key_terms = extract_key_terms(original)

    # Generate variants

    variants = generate_query_variants(original)

    # The "optimized" query is the abbreviation-expanded
    # version for primary use

    optimized = expand_abbreviations(original)

    return {
        "original": original,
        "optimized": optimized,
        "variants": variants,
        "key_terms": key_terms,
    }


# ============================================================
# MERGE AND DEDUPLICATE RESULTS
# ============================================================


def merge_search_results(result_sets, max_results=10):
    """
    Merges multiple sets of search results (from different
    query variants), deduplicates by content, and returns
    the top results ranked by their best score.

    Each result_set is a list of dicts with at least:
        text, score (or bm25_score)

    Returns a merged list sorted by best score.
    """

    # Track best score for each unique text

    seen_texts = {}

    for result_set in result_sets:

        for result in result_set:

            text = result.get("text", "")

            # Use a content fingerprint for dedup

            fingerprint = text.strip().lower()[:200]

            score = result.get("score", result.get("bm25_score", 0.0))

            if fingerprint in seen_texts:

                # Keep the higher score

                existing = seen_texts[fingerprint]

                if score > existing.get("score", 0):

                    seen_texts[fingerprint] = {**result, "score": score}

            else:

                seen_texts[fingerprint] = {**result, "score": score}

    # Sort by score descending

    merged = sorted(
        seen_texts.values(),
        key=lambda r: r.get("score", 0),
        reverse=True,
    )

    return merged[:max_results]
