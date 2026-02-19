import json
from app.core.config import BLOGS_URL_PATH


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