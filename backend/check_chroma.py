import chromadb


print("\n========================================")
print("       CHROMADB STORAGE CHECK")
print("========================================\n")


# Connect to SAME ChromaDB folder
client = chromadb.PersistentClient(
    path="chroma_db"
)


# Get SAME collection
collection = client.get_or_create_collection(
    name="documents"
)


# Count records
total_records = collection.count()

print("Collection Name: documents")
print("ChromaDB Path: chroma_db")
print(f"Total Vectors/Chunks Stored: {total_records}")


if total_records == 0:
    print("\nNo data is currently stored in ChromaDB.")
else:

    # Get everything
    data = collection.get(
        include=[
            "documents",
            "metadatas",
            "embeddings"
        ]
    )


    print("\n========================================")
    print("STORED RECORDS")
    print("========================================")


    for i in range(total_records):

        record_id = data["ids"][i]
        document = data["documents"][i]
        metadata = data["metadatas"][i]
        embedding = data["embeddings"][i]


        print(f"\n---------- RECORD {i + 1} ----------")

        print(f"ID: {record_id}")

        print(
            f"Source File: "
            f"{metadata.get('source', 'Unknown')}"
        )

        print(
            f"Chunk Number: "
            f"{metadata.get('chunk_number', 'Unknown')}"
        )

        print(
            f"Embedding Dimension: "
            f"{len(embedding)}"
        )

        print(
            f"Embedding Preview: "
            f"{embedding[:10]}"
        )

        print("\nChunk Text:")
        print(document[:500])

        print("\n------------------------------------")


print("\n========================================")
print("           STORAGE SUMMARY")
print("========================================")

print(f"Total chunks stored: {total_records}")
print(f"Total embeddings stored: {total_records}")

if total_records > 0:
    print(
        f"Embedding dimension: "
        f"{len(data['embeddings'][0])}"
    )

print("========================================\n")