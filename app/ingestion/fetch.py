import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import feedparser
import logging

from app.core.config import BLOGS_URL, BLOGS_URL_PATH, PODCASTS_URL, PODCASTS_URL_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_registry(path) -> dict:
    if path.exists():
        if str(path).lower() == str(BLOGS_URL_PATH).lower():
            with open(path, "r", encoding="utf-8") as f:
                # For multiple URLs (dicts) in a list
                return {item["blog_id"]: item for item in json.load(f)} 
                #For Single URL (dict) without list
                # return {json.load(f)['blog_id']}
        else:
            with open(path, "r", encoding="utf-8") as f:
                # For multiple URLs (dicts) in a list
                return {item["episode_id"]: item for item in json.load(f)} 
                # For Single url (dict) without list
                # return {json.load(f)['episode_id']}
    return {}

def save_registry(path, registry: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(registry.values()), f, ensure_ascii=False, indent=2)

def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

def fetch_page(url: str) -> BeautifulSoup:
    logging.info(f"URL TO FETCH: {url}")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def filter_article(path: str) -> bool:
    parts = path.strip("/").split("/")
    return (
        path.startswith("/blog/")
        and len(parts) == 2
        and parts[1] not in {"archives", "author", "previous"}
    )

def fetch_rss_feed():
    feed = feedparser.parse(PODCASTS_URL)
    if feed.boze:
        raise RuntimeError(f"Failed to fetch RSS feed")

    return feed

def blog_fetcher():
    registry = load_registry(BLOGS_URL_PATH)
    visited_pages = set()

    pages_to_visit = {"/blog"}
    page_index = 1

    while pages_to_visit:
        path = pages_to_visit.pop()
        visited_pages.add(path)
        links_with_titles = []
        
        full_page_url = normalize_url(urljoin(BLOGS_URL, path))
        logger.info(f"[VISIT] {full_page_url}")

        # Fetch raw html page
        try:
            soup = fetch_page(full_page_url)
        except Exception as e:
            logger.error(f"[ERROR] {full_page_url}: {e}")
            continue

        # Find all links with titles
        for a in soup.find_all("a", href=True):
            href = a["href"].split("#")[0].strip()
            title = a.get_text(strip=True)

            if not href or not title:
                continue
            
            logger.info(f"HERF: {href}, TITLE: {title}")
            links_with_titles.append((href, title))
        
        for href, title in links_with_titles:
            parsed = urlparse(href)
            link_path = parsed.path

            # Check if it is article
            if filter_article(link_path):
                article_url = normalize_url(urljoin(BLOGS_URL, link_path))
                # Generate blog ID
                blog_id = hashlib.sha1(article_url.encode("utf-8")).hexdigest()

                if blog_id not in registry:
                    registry[blog_id] = {
                        "blog_id": blog_id,
                        "title": title,
                        "url": article_url,
                        "state": "DISCOVERED",
                        "last_checked": datetime.now(timezone.utc).isoformat()
                    }
        
        # Pagination Control
        next_page = f"/blog/previous/{page_index}"
        if next_page not in visited_pages:
            pages_to_visit.add(next_page)
            page_index += 1

    save_registry(BLOGS_URL_PATH, registry)
    logger.info(f"Total blogs discovered: {len(registry)}")

def podcast_fetcher():
    registry = load_registry(PODCASTS_URL_PATH)
    feed = fetch_rss_feed()

    discovered = 0

    for entry in feed.entries:
        title = getattr(entry, "title", "Untitled Episode")
        published = getattr(entry, "published")

        audio_url = None
        if getattr(entry, "enclosures", None):
            audio_url = entry.enclosures[0].href
        
        if not audio_url:
            continue

        episode_id = getattr(entry, "id", None)
        if not episode_id:
            episode_id = f"Buzzsprout-{audio_url.split('/')[-1].replace('.mp3','')}"

        if episode_id in registry:
            continue

        episode_url = audio_url.replace(".mp3", "")

        registry[episode_id] = {
            "episode_id": episode_id,
            "title": title,
            "episode_url": episode_url,
            "audio_url": audio_url,
            "published": published,
            "state": "DISCOVERED",
            "last_checked": datetime.now(timezone.utc).isoformat()
        }

        discovered += 1

    save_registry(PODCASTS_URL_PATH, registry)
    logger.info(f"Total episodes discovered: {discovered}")

if __name__ == "__main__":
    blog_fetcher()