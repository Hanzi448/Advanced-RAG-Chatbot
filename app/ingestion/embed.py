import json
import logging
from pathlib import Path
import time

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings


from app.core.config import (
    BLOGS_CHUNKS_PATH,
    PODCASTS_CHUNKS_PATH,
    GEMINI_EMBED_MODEL,
    GEMINI_API_KEY,
    EMBEDDING_PATH
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3

embeddings = GoogleGenerativeAIEmbeddings(
    model=GEMINI_EMBED_MODEL,
    google_api_key=GEMINI_API_KEY,
    task_type="retrieval_document"
)

def get_vectorstore(collection_name: str) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(EMBEDDING_PATH),
        collection_metadata={"hnsw:space": "cosine"}
    )

def load_chunks(path: Path) -> list[dict]:
    if not path.exists():
        logger.warning(f"[SKIP] Chunks file not found: {path}")
        return []
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest_chunks(chunks: list[dict], collection_name: str):
    if not chunks:
        logger.info(f"[SKIP] No chunks for {collection_name}")
        return
    
    vectorstore = get_vectorstore(collection_name, embeddings)

    existing = vectorstore.get()

    # Extracting all current chunk IDs
    existing_ids = set(existing["ids"]) if existing and existing.get("ids") else set()

    logger.info(f"[INFO] {collection_name} | Existing Vectors: {len(existing_ids)}")

    new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]

    if not new_chunks:
        logger.info(f"[DONE] No new chunks to embed for {collection_name}")
        return 
    
    logger.info(f"[START] Embedding {len(new_chunks)} chunks -> {collection_name}")

    success = 0
    failed = 0

    for idx, chunk in enumerate(new_chunks, start=1):
        chunk_id = chunk["chunk_id"]

        logger.info(f"[EMBED] {collection_name} | {idx}/{len(new_chunks)} | {chunk_id}") 

        retries = 0
        while retries < MAX_RETRIES:
            try:
                vectorstore.add_texts(
                    texts=[chunk["text"]],
                    ids=[chunk_id],
                    metadatas=[{
                        "parent_id": chunk["parent_id"],
                        "source_type": chunk["source_type"],
                        "title": chunk["title"],
                        "source_url": chunk["source_url"],
                    }],
                )

                success += 1
                break

            except Exception as e:
                retries += 1
                logger.error(
                    f"[RETRY] {collection_name} | {chunk_id} "
                    f"({retries}/{MAX_RETRIES} | {e})"
                )
                time.sleep(2 * retries)

        if retries == MAX_RETRIES:
            failed += 1
            logger.error(f"[FAIL] {collection_name} | {chunk_id}")
    
    logger.info(f"[DONE] {collection_name} | Embedded: {success} | Failed: {failed}")


def embedder():
    blog_chunks = load_chunks(BLOGS_CHUNKS_PATH)
    ingest_chunks(blog_chunks, "blogs")

    podcast_chunks = load_chunks(PODCASTS_CHUNKS_PATH)
    ingest_chunks(podcast_chunks, "podcasts")

if __name__ == "__main__":
    embedder()