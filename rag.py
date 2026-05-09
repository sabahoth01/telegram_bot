import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.config import Settings
import logging

logger = logging.getLogger(__name__)

EMBED_MODEL = "all-MiniLM-L6-v2"  # small, fast, runs on CPU, ~80MB
COLLECTION_NAME = "bigdata_course"
N_RESULTS = 4  # how many chunks to retrieve per query

# Lazy-loaded singletons
_embedder = None
_collection = None


def get_embedder():
    global _embedder
    if _embedder is None:
        logger.info("Loading embedding model...")
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path="/app/chroma_db",
                                          settings=Settings(anonymized_telemetry=False) )
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def retrieve(query: str, n_results: int = N_RESULTS) -> str:
    """Find the most relevant course chunks for a query."""
    collection = get_collection()

    if collection.count() == 0:
        return ""  # no docs ingested yet

    embedder = get_embedder()
    query_vector = embedder.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas"]
    )

    chunks = results["documents"][0]
    metas = results["metadatas"][0]

    # Format retrieved context
    context_parts = []
    for chunk, meta in zip(chunks, metas):
        source = meta.get("source", "unknown")
        context_parts.append(f"[{source}]\n{chunk}")

    return "\n\n".join(context_parts)