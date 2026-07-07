import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
BOT_USERNAME = os.getenv("BOT_USERNAME", "NextGuardMusicbot").strip().lstrip("@")

ENABLE_YTDLP = os.getenv("ENABLE_YTDLP", "0").strip() == "1"
DOWNLOAD_DIR = BASE_DIR / os.getenv("DOWNLOAD_DIR", "downloads")
MAX_DOWNLOAD_MB = int(os.getenv("MAX_DOWNLOAD_MB", "50") or 50)

DB_PATH = BASE_DIR / "music.db"
DOWNLOAD_DIR.mkdir(exist_ok=True)
