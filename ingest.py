import os
import hashlib
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
import logging
from chromadb.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

DOCS_DIR = "/app/course_docs"
CHROMA_DIR = "/app/chroma_db"
COLLECTION_NAME = "bigdata_course"
EMBED_MODEL = "all-MiniLM-L6-v2"

CHUNK_SIZE = 500        # characters per chunk
CHUNK_OVERLAP = 50      # overlap between chunks


def load_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def load_file(path: str) -> str | None:
    ext = Path(path).suffix.lower()
    if ext in [".txt", ".md"]:
        return load_txt(path)
    elif ext == ".pdf":
        return load_pdf(path)
    else:
        logger.warning(f"Skipping unsupported file: {path}")
        return None


def chunk_text(text: str, source: str) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_text(text)
    return [
        {
            "text": chunk,
            "id": hashlib.md5(f"{source}_{i}_{chunk[:50]}".encode()).hexdigest(),
            "metadata": {"source": Path(source).name, "chunk_index": i}
        }
        for i, chunk in enumerate(chunks)
        if chunk.strip()
    ]


def ingest():
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        logger.warning(f"Created {DOCS_DIR}/ — add your course files there and re-run.")
        return

    # Collect all files
    all_files = []
    for root, _, files in os.walk(DOCS_DIR):
        for file in files:
            all_files.append(os.path.join(root, file))

    if not all_files:
        logger.warning(f"No files found in {DOCS_DIR}/")
        return

    # Load and chunk
    all_chunks = []
    for filepath in all_files:
        logger.info(f"Loading: {filepath}")
        text = load_file(filepath)
        if text and text.strip():
            chunks = chunk_text(text, filepath)
            all_chunks.extend(chunks)
            logger.info(f"  → {len(chunks)} chunks")

    if not all_chunks:
        logger.warning("No content extracted from files.")
        return

    # Embed
    logger.info(f"Embedding {len(all_chunks)} chunks with {EMBED_MODEL}...")
    embedder = SentenceTransformer(EMBED_MODEL)
    texts = [c["text"] for c in all_chunks]
    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()

    # Store in ChromaDB
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    # Clear existing collection to avoid duplicates on re-ingest
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    collection.add(
        ids=[c["id"] for c in all_chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[c["metadata"] for c in all_chunks]
    )

    logger.info(f"Ingested {len(all_chunks)} chunks from {len(all_files)} files into ChromaDB.")


if __name__ == "__main__":
    ingest()