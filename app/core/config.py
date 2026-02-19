import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Whsiper
MODEL_SIZE = "tiny.en"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_EMBED_MODEL = "models/gemini-embedding-001"
GEMINI_LLM_MODEL = "models/gemini-2.5-flash"

# Data

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
EMBEDDING_PATH = DATA_DIR / "embeddings"
RAW_BLOGS_DIR = DATA_DIR / "raw" / "blogs"
RAW_PODCASTS_DIR = DATA_DIR / "raw" / "podcasts"
BLOGS_URL_PATH = DATA_DIR / "registry" / "blogs_urls.json"
PODCASTS_URL_PATH = DATA_DIR / "registry" / "podcasts_urls.json"
BLOGS_CHUNKS_PATH = DATA_DIR / "processed" / "blogs" / "blogs_chunks.json"
PODCASTS_CHUNKS_PATH = DATA_DIR / "processed" / "podcasts" / "podcasts_chunks.json"
PODCASTS_AUDIO_PATH = DATA_DIR / "audio" / "podcasts"
VIDEOS_AUDIO_PATH = DATA_DIR / "audio" / "videos"

# URLs
BLOGS_URL = "https://www.challengerstrength.com/blog"
PODCASTS_URL = "https://rss.buzzsprout.com/238054.rss"


 # Extras
CHECK_INTERVAL_HOURS = 24
