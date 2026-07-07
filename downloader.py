from pathlib import Path
from .config import ENABLE_YTDLP, DOWNLOAD_DIR, MAX_DOWNLOAD_MB

async def download_online(query_or_url: str, quality="128"):
    """
    اسکلت دانلود آنلاین.
    برای فعال شدن:
    ENABLE_YTDLP=1
    همچنین بهتر است ffmpeg نصب باشد.
    خروجی: path یا None
    """
    if not ENABLE_YTDLP:
        return None, "دانلود آنلاین غیرفعال است."

    try:
        import yt_dlp
    except Exception as e:
        return None, f"yt-dlp نصب نیست: {e}"

    outtmpl = str(DOWNLOAD_DIR / "%(title).80s-%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "max_filesize": MAX_DOWNLOAD_MB * 1024 * 1024,
        "quiet": True,
        "default_search": "ytsearch1",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320" if quality == "320" else "128",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query_or_url, download=True)
            if "entries" in info:
                info = info["entries"][0]
            filename = ydl.prepare_filename(info)
            mp3 = Path(filename).with_suffix(".mp3")
            return mp3 if mp3.exists() else Path(filename), None
    except Exception as e:
        return None, str(e)
