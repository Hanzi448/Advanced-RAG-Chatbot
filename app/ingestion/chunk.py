import json
import logging
from pathlib import Path
import hashlib
from typing import List, Dict
import tiktoken

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import (
    BLOGS_CHUNKS_PATH,
    PODCASTS_CHUNKS_PATH,
    RAW_BLOGS_DIR,
    RAW_PODCASTS_DIR,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80

_encoding = tiktoken.get_encoding("cl100k_base")

def _token_len(text: str) -> int:
    return len(_encoding.encode(text))

_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", ". ", " ", ""],
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=_token_len,
)

def stable_chunk_id(parent_id: str, chunk_index: int, text: str) -> str:
    raw = f"{parent_id}:{chunk_index}:{text}".encode('utf-8')
    return hashlib.sha1(raw).hexdigest()

def split_text(*, text: str, parent_id: str, source_type: str, title: str, source_url: str) -> List[Dict]:
    chunks = []

    for chunk_index, chunk_text in enumerate(_splitter.split_text(text)):
        chunk_text = chunk_text.strip()
        if not chunk_text:
            continue

        chunks.append({
            "chunk_id": stable_chunk_id(parent_id, chunk_index, chunk_text),
            "parent_id": parent_id,
            "source_type": source_type,
            "title": title,
            "source_url": source_url,
            "chunk_index": chunk_index,
            "text": chunk_text
        })

    return chunks


def load_raw_items(raw_dir: Path) -> list[dict]:
    items = []

    for file in raw_dir.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                items.append(json.load(f))
        except Exception as e:
            logger.error(f"[ERROR] Failed reading {file.name}: {e}")
    
    return items


def save_chunks(chunks: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)


def process_blogs():
    logger.info("Processing blogs")
    all_chunks = []

    for blog in load_raw_items(RAW_BLOGS_DIR):
        text = blog.get("content", "").strip()
        if not text:
            continue

        all_chunks.extend(split_text(
            text=text,
            parent_id=blog["blog_id"],
            source_type="blog",
            title=blog.get("title", ""),
            source_url=blog.get("url", "")
        ))

    save_chunks(all_chunks, BLOGS_CHUNKS_PATH)
    logger.info(f"[DONE] Blog chunks: {len(all_chunks)}")


def process_podcasts():
    logger.info("Processing podcasts")
    all_chunks = []

    for episode in load_raw_items(RAW_PODCASTS_DIR):
        text = episode.get("transcript", "").strip()
        if not text:
            continue

        all_chunks.extend(split_text(
            text=text,
            parent_id=episode["episode_id"],
            source_type="podcast",
            title=episode.get("title", ""),
            source_url=episode.get("episode_url", "")
        ))

    save_chunks(all_chunks, PODCASTS_CHUNKS_PATH)
    logger.info(f"[DONE] Podcast chunks: {len(all_chunks)}")


def chunker():
    process_blogs()
    process_podcasts()


if __name__ == "__main__":
    chunker()