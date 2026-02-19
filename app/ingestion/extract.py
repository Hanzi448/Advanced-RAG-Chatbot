import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from app.ingestion.fetch import fetch_page
from app.ingestion.transcriber import audio_downloader, audio_transcriber
from app.ingestion.storage import load_registry, save_registry
from app.core.config import (
    BLOGS_URL_PATH,
    RAW_BLOGS_DIR,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    text = "\n".join(lines)
    logging.info("--- Cleaned Article ---")
    logging.info(f"ARTICLE: {text}")
    return text


def extract_main_content(soup: BeautifulSoup) -> str:
    # remove extra stuff
    for tag in soup(["script", "style", "nav", "footer", "aside"]):
        tag.decompose()

    # article tag
    article = soup.find("article")
    if article:
        article_text = article.get_text(separator="\n")
        return clean_text(article_text)
    
    # common containers
    for cls in ["post-content", "entry-content", "blog-post"]:
        div = soup.find("div", class_=cls)
        if div:
            return clean_text(div.get_text(separator="\n"))
        
    candidates = soup.find_all("div")
    best = max(
        candidates,
        key = lambda d: len(d.get_text(strip=True)),
        default=None
    )

    if best:
        return clean_text(best.get_text(separator="\n"))
    
    return ""


def extract_title(soup: BeautifulSoup) -> str | None:
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    
    if soup.title:
        return soup.title.get_text(strip=True)
    
    return None


def blog_extractor():
    registry = load_registry(BLOGS_URL_PATH)
    # Save raw text of blogs in {blog_id}.json file
    RAW_BLOGS_DIR.mkdir(parents=True, exist_ok=True)

    processed = 0

    for blog_id, item in registry.items():
        # Skips the already extracted URLs
        if item.get("state") != "DISCOVERED":
            continue

        url = item.get("url")
        logger.info("\n--- Fetching ---\n")
        logger.info(f"[FETCH] {url}")

        try:
            soup = fetch_page(url)
            content = extract_main_content(soup)
            if not content:
                raise ValueError("Empty content extracted")
            
            title = extract_title(soup)
            if title:
                item["title"] = title

            raw_data = {
                "blog_id": blog_id,
                "title": item.get("title", ""),
                "url": url,
                "content": content,
                "extracted_at": datetime.now(timezone.utc).isoformat()
            }

            out_path = RAW_BLOGS_DIR / f"{blog_id}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)

            item["state"] = "FETCHED_RAW"
            item["last_checked"] = datetime.now(timezone.utc).isoformat()

            processed += 1

        except Exception as e:
            logger.error(f"[ERROR] {url} | {e}")
            item["state"] = "FAILED_RAW"
            item["last_checked"] = datetime.now(timezone.utc).isoformat()

        
    save_registry(BLOGS_URL_PATH, registry)
    logger.info(f"[DONE] Blog raw extraction complete: {processed}")

def podcasts_extractor():
    # audio_downloader()
    audio_transcriber()

if __name__ == "__main__":
    # blog_extractor()
    podcasts_extractor()