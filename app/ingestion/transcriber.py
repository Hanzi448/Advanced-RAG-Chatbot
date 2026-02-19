import json
import requests
import logging
from pathlib import Path
from datetime import datetime, timezone
from faster_whisper import WhisperModel

from app.ingestion.storage import load_registry, save_registry
from app.core.config import (
    PODCASTS_URL_PATH,
    PODCASTS_AUDIO_PATH,
    RAW_PODCASTS_DIR,
    MODEL_SIZE,
    COMPUTE_TYPE,
    DEVICE
    )


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
DEV_MAX_EPISODES = 10 # DEV ONLY - set to None for production

model = WhisperModel(
    MODEL_SIZE,
    device=DEVICE,
    compute_type=COMPUTE_TYPE,
)

def download_audio(audio_url: str, episode_id: str) -> Path:
    PODCASTS_AUDIO_PATH.mkdir(parents=True, exist_ok=True)
    audio_path = PODCASTS_AUDIO_PATH / f"{episode_id}.mp3"

    if audio_path.exists():
        logger.info(f"[SKIP] Audio already exists: {audio_path}")
        return audio_path
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://www.buzzsprout.com/"
    }

    logger.info(f"[DOWNLOAD] {episode_id}")

    with requests.get(audio_url, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(audio_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8162):
                if chunk:
                    f.write(chunk)

    return audio_path

def audio_downloader():
    registry = load_registry(PODCASTS_URL_PATH)
    downloaded = 0
    processed = 0 #Dev only

    for episode_id, item in registry.items():
        if DEV_MAX_EPISODES and processed >= DEV_MAX_EPISODES: #Dev only
            logger.info("[DEV] Epsiode limit reached")
            break

        if item["state"] not in {"DISCOVERED", "AUDIO_FAILED"}:
            continue

        retries = item.get("retries", 0)
        if retries >= MAX_RETRIES:
            continue

        try:
            download_audio(item["audio_url"], episode_id)

            item["state"] = "AUDIO_DOWNLOADED"
            item["last_checked"] = datetime.now(timezone.utc).isoformat()
            item.pop("retries", None)

            downloaded += 1
            processed += 1 # Dev only

        except Exception as e:
            logger.error(f"[ERROR] {episode_id} | {e}")

            item["state"] = "AUDIO_FAILED"
            item["retries"] = retries + 1
            item["last_checked"] = datetime.now(timezone.utc).isoformat()

    save_registry(PODCASTS_URL_PATH, registry)
    logger.info(f"[DONE] Audio downloaded: {downloaded}")


def transcribe_audio(audio_path: Path) -> str | None:
    logger.info(f"[TRANSCRIBE] {audio_path.name}")

    try:
        segments, _ = model.transcribe(
            str(audio_path),
            language="en",
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False
        )

        transcript = " ".join(seg.text.strip() for seg in segments).strip()
        return transcript if transcript else None
    
    except Exception as e:
        logger.error(f"[FAILED] Transcription error | {e}")
        return None

def save_raw_transcript(episode_id: str, item: dict, transcript: str):
    RAW_PODCASTS_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_PODCASTS_DIR / f"{episode_id}.json"

    raw_payload = {
        "episode_id": episode_id,
        "title": item["title"],
        "episode_url": item["episode_url"],
        "audio_url": item["audio_url"],
        "published_at": item["published_at"],
        "transcript": transcript
    }

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=2, ensure_ascii=False)

def audio_transcriber():
    registry = load_registry(PODCASTS_URL_PATH)
    completed = 0

    for episode_id, item in registry.items():
        if item["state"] != "AUDIO_DOWNLOADED":
            continue

        audio_path = PODCASTS_AUDIO_PATH / f"{episode_id}.mp3"
        if not audio_path.exists():
            logger.warning(f"[MISSING AUDIO] {episode_id}")
            continue

        retries = item.get("retries", 0)
        if retries >= MAX_RETRIES:
            continue

        transcript = transcribe_audio(audio_path)

        if transcript:
            save_raw_transcript(episode_id, item, transcript)

            # delete audio after success
            audio_path.unlink(missing_ok=True)

            item["state"] = "TRANSCRIBED"
            item["last_checked"] = datetime.now(timezone.utc).isoformat()
            item.pop("retries", None)

            completed += 1
            logger.info(f"[DONE] {episode_id}")

        else:
            item["retries"] = retries + 1
            item["last_checked"] = datetime.now(timezone.utc).isoformat()
            logger.error(f"[RETRY] {episode_id} ({item['retries']})")

    save_registry(PODCASTS_URL_PATH, registry)
    logger.info(f"[ALL DONE] Transcription complete: {completed}")