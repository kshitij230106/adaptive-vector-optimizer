import re

# ============================================================
# TEXT CLEANING
# ============================================================


def clean_text(text):
    """
    Removes unnecessary whitespace and line breaks.
    """

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# EXTRACT TABLE FIELDS
# ============================================================


def extract_table_fields(text):
    """
    Extracts database table fields from text.

    Example:

    EMP_ID PRIMARY KEY NUMBER(6)
    FIRST_NAME VARCHAR2(20)
    LAST_NAME NOT NULL VARCHAR2(25)

    becomes:

    EMP_ID       -> NUMBER(6)       -> PRIMARY KEY
    FIRST_NAME   -> VARCHAR2(20)
    LAST_NAME    -> VARCHAR2(25)    -> NOT NULL
    """

    text = clean_text(text)

    # Database constraints commonly found in table definitions
    constraint_pattern = (
        r"(?:(?:PRIMARY\s+KEY|"
        r"FOREIGN\s+KEY|"
        r"NOT\s+NULL|"
        r"UNIQUE|"
        r"CHECK)"
        r"\s*)*"
    )

    # Common SQL data types
    datatype_pattern = (
        r"(?:"
        r"NUMBER"
        r"(?:\s*\(\s*\d+\s*(?:,\s*\d+\s*)?\))?"
        r"|"
        r"VARCHAR2"
        r"(?:\s*\(\s*\d+\s*\))?"
        r"|"
        r"CHAR"
        r"(?:\s*\(\s*\d+\s*\))?"
        r"|"
        r"DATE"
        r"|"
        r"TIMESTAMP"
        r")"
    )

    pattern = re.compile(
        r"\b([A-Z][A-Z0-9_]*)\s+" + constraint_pattern + r"(" + datatype_pattern + r")",
        re.IGNORECASE,
    )

    matches = pattern.finditer(text)

    fields = []

    for match in matches:

        field_name = match.group(1).upper()

        datatype = clean_text(match.group(2)).upper()

        # Ignore obvious non-column words
        ignored_words = {
            "COLUMN",
            "NAME",
            "CONSTRAINT",
            "TYPE",
            "DATA",
            "EMPLOYEE",
            "TABLE",
            "CREATE",
            "INSERT",
            "DISPLAY",
            "NUMBER",
            "VARCHAR2",
            "DATE",
        }

        if field_name in ignored_words:
            continue

        # Find the text between field name and datatype
        full_match = match.group(0)

        datatype_position = full_match.upper().rfind(datatype.upper())

        constraint_text = full_match[len(field_name) : datatype_position].strip()

        constraint_text = clean_text(constraint_text).upper()

        fields.append(
            {"name": field_name, "datatype": datatype, "constraints": constraint_text}
        )

    return fields


# ============================================================
# FORMAT TABLE ANSWER
# ============================================================


def format_table_answer(fields):
    """
    Converts extracted fields into a readable answer.
    """

    if not fields:

        return None

    lines = []

    lines.append("The EMPLOYEE table contains the following fields:")

    lines.append("")

    for field in fields:

        line = f"- {field['name']} → " f"{field['datatype']}"

        if field["constraints"]:

            line += f" → {field['constraints']}"

        lines.append(line)

    return "\n".join(lines)


# ============================================================
# QUERY TYPE DETECTION
# ============================================================


def is_table_field_query(query):
    """
    Determines whether the user is asking about
    table fields, columns, or data types.
    """

    query_lower = query.lower()

    keywords = [
        "fields",
        "columns",
        "data types",
        "datatype",
        "table structure",
        "table definition",
        "create table",
    ]

    return any(keyword in query_lower for keyword in keywords)


# ============================================================
# EXTRACT RELEVANT SENTENCES
# ============================================================


def extract_relevant_sentences(query, documents, max_sentences=5):
    """
    Extracts sentences that share important words
    with the user's query.
    """

    stop_words = {
        "what",
        "is",
        "are",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "for",
        "and",
        "or",
        "how",
        "which",
        "who",
        "does",
        "do",
        "this",
        "that",
        "with",
        "on",
        "from",
        "tell",
        "me",
        "about",
    }

    query_words = set(
        word.lower()
        for word in re.findall(r"\b[a-zA-Z0-9_]+\b", query)
        if word.lower() not in stop_words
    )

    candidate_sentences = []

    for document in documents:

        cleaned_document = clean_text(document)

        sentences = re.split(r"(?<=[.!?])\s+", cleaned_document)

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            sentence_words = set(
                word.lower() for word in re.findall(r"\b[a-zA-Z0-9_]+\b", sentence)
            )

            matching_words = query_words & sentence_words

            score = len(matching_words)

            if score > 0:

                candidate_sentences.append((score, sentence))

    candidate_sentences.sort(key=lambda item: item[0], reverse=True)

    selected_sentences = []

    seen = set()

    for score, sentence in candidate_sentences:

        normalized = sentence.lower()

        if normalized in seen:
            continue

        seen.add(normalized)

        selected_sentences.append(sentence)

        if len(selected_sentences) >= max_sentences:
            break

    return selected_sentences


# ============================================================
# GENERATE ANSWER
# ============================================================


def generate_answer(query, search_results):
    """
    Generates an extractive answer from retrieved
    ChromaDB results.

    No LLM is used.
    """

    # --------------------------------------------------------
    # NO RESULTS
    # --------------------------------------------------------

    if not search_results:

        return {
            "answer": (
                "No relevant information was found " "in the uploaded documents."
            ),
            "sources": [],
        }

    documents = [result["text"] for result in search_results]

    # --------------------------------------------------------
    # TABLE / FIELD QUERY
    # --------------------------------------------------------

    if is_table_field_query(query):

        all_fields = []

        for document in documents:

            fields = extract_table_fields(document)

            for field in fields:

                # Avoid duplicates
                if field not in all_fields:

                    all_fields.append(field)

        if all_fields:

            answer = format_table_answer(all_fields)

        else:

            answer = (
                "The relevant document content was found, "
                "but the table fields could not be "
                "structured automatically.\n\n"
            )

            relevant_sentences = extract_relevant_sentences(
                query=query, documents=documents, max_sentences=5
            )

            answer += " ".join(relevant_sentences)

    # --------------------------------------------------------
    # GENERAL QUESTION
    # --------------------------------------------------------

    else:

        relevant_sentences = extract_relevant_sentences(
            query=query, documents=documents, max_sentences=5
        )

        if not relevant_sentences:

            answer = (
                "Relevant document content was found, "
                "but no specific answer could be extracted."
            )

        else:

            answer = " ".join(relevant_sentences)

    # --------------------------------------------------------
    # SOURCE INFORMATION
    # --------------------------------------------------------

    sources = []

    for result in search_results:

        source = {
            "source": result.get("source", "Unknown"),
            "chunk_number": result.get("chunk_number", "Unknown"),
        }

        if source not in sources:

            sources.append(source)

    # --------------------------------------------------------
    # RETURN ANSWER
    # --------------------------------------------------------

    return {"answer": answer, "sources": sources}
