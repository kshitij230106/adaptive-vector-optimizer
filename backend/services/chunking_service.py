def create_chunks(
    text,
    chunk_size=1000,
    overlap=100
):

    # Remove unnecessary spaces
    text = " ".join(text.split())

    if not text:
        return []


    chunks = []

    start = 0
    text_length = len(text)


    while start < text_length:

        end = start + chunk_size

        chunk = text[start:end]

        # Don't add empty chunks
        if chunk.strip():
            chunks.append(chunk)


        # Last chunk 
        if end >= text_length:
            break


        # Move forward with overlap
        start = end - overlap


    return chunks