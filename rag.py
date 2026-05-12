# import chromadb
# from sentence_transformers import SentenceTransformer
# from chromadb.config import Settings
# import logging

# logger = logging.getLogger(__name__)

# EMBED_MODEL = "all-MiniLM-L6-v2"
# COLLECTION_NAME = "bigdata_course"
# N_RESULTS = 2

# logger.info("Loading embedding model once at startup...")
# _embedder = SentenceTransformer(EMBED_MODEL)

# client = chromadb.PersistentClient(
#     path="/app/chroma_db",
#     settings=Settings(anonymized_telemetry=False)
# )

# _collection = client.get_or_create_collection(
#     name=COLLECTION_NAME,
#     metadata={"hnsw:space": "cosine"}
# )


# def retrieve(query: str, n_results: int = N_RESULTS) -> str:
#     collection = _collection

#     if collection.count() == 0:
#         return ""

#     query_vector = _embedder.encode(query).tolist()

#     results = collection.query(
#         query_embeddings=[query_vector],
#         n_results=min(n_results, collection.count()),
#         include=["documents", "metadatas"]
#     )

#     chunks = results["documents"][0]
#     metas = results["metadatas"][0]

#     context_parts = []
#     for chunk, meta in zip(chunks, metas):
#         source = meta.get("source", "unknown")
#         context_parts.append(f"[{source}]\n{chunk}")

#     return "\n\n".join(context_parts)

import logging
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

EMBED_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "bigdata_course"
CHROMA_DIR = "/app/chroma_db"
N_RESULTS = 2

logger.info("Loading embedding model once at startup...")
embedder = SentenceTransformer(EMBED_MODEL)

client = chromadb.PersistentClient(
    path=CHROMA_DIR,
    settings=Settings(anonymized_telemetry=False)
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)


def retrieve(query: str, n_results: int = N_RESULTS) -> str:
    query = query.strip()

    if not query:
        return ""

    count = collection.count()

    if count == 0:
        logger.warning("Chroma collection is empty. Run ingestion first.")
        return ""

    query_vector = embedder.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(n_results, count),
        include=["documents", "metadatas"]
    )

    chunks = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    if not chunks:
        return ""

    context_parts = []

    for chunk, meta in zip(chunks, metas):
        source = meta.get("source", "unknown") if meta else "unknown"
        context_parts.append(f"[{source}]\n{chunk}")

    return "\n\n".join(context_parts)