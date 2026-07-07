TEXTS = {
    "fa": {
        "start": "🎵 NextGuard Music\n\nبه موزیک پلیر حرفه‌ای نکست گارد خوش آمدی.",
        "not_found": "موزیکی پیدا نشد.",
        "empty": "آرشیو موزیک خالی است.",
        "admin_only": "⛔ فقط مالک یا ادمین ربات.",
    },
    "en": {
        "start": "🎵 NextGuard Music\n\nWelcome to NextGuard professional music player.",
        "not_found": "No music found.",
        "empty": "Music archive is empty.",
        "admin_only": "Admins only.",
    },
    "uz": {
        "start": "🎵 NextGuard Music\n\nNextGuard musiqa botiga xush kelibsiz.",
        "not_found": "Musiqa topilmadi.",
        "empty": "Arxiv bo‘sh.",
        "admin_only": "Faqat adminlar.",
    },
    "ps": {
        "start": "🎵 NextGuard Music\n\nد NextGuard Music ته ښه راغلاست.",
        "not_found": "موزیک ونه موندل شو.",
        "empty": "ارشیف تش دی.",
        "admin_only": "یوازې اډمین.",
    }
}

def t(key, lang="fa"):
    return TEXTS.get(lang, TEXTS["fa"]).get(key, TEXTS["fa"].get(key, key))
