import json
from app.core.config import BLOGS_CHUNKS_PATH, PODCASTS_CHUNKS_PATH
import tiktoken

total_chunks = 0
total_podcast_chunks = 0

_encoding = tiktoken.get_encoding("cl100k_base")

print("\nBLOGS CHUNKS:")
with open(BLOGS_CHUNKS_PATH, "r", encoding="utf-8") as f:
    for item in json.load(f):
        print(f"CHUNK LENGTH: {len(_encoding.encode(item['text']))}")
        total_chunks += 1

print("\nPODCASTS CHUNKS:")
with open(PODCASTS_CHUNKS_PATH, "r", encoding="utf-8") as f:
    for item in json.load(f):
        print(f"CHUNK LENGTH: {len(_encoding.encode(item['text']))}")
        total_podcast_chunks += 1

print(f"Total Blog Chunks: {total_chunks}")
print(f"Total Podcast Chunks: {total_podcast_chunks}")