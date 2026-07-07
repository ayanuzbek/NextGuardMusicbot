import os
import sqlite3
import random
import logging
from pathlib import Path
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "music.db"

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or "0")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("NextGuardMusic")


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT DEFAULT '',
        category TEXT DEFAULT 'عمومی',
        file_id TEXT NOT NULL,
        file_unique_id TEXT DEFAULT '',
        duration INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TEXT,
        plays INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS favorites (
        user_id INTEGER NOT NULL,
        track_id INTEGER NOT NULL,
        created_at TEXT,
        PRIMARY KEY(user_id, track_id)
    );

    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
    );
    """)
    if OWNER_ID:
        con.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (OWNER_ID,))
    con.commit()
    con.close()


def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    con = db()
    row = con.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    return bool(row)


def main_keyboard(user_id: int):
    rows = [
        [InlineKeyboardButton("🔎 جستجوی موزیک", callback_data="music_help")],
        [InlineKeyboardButton("🎲 موزیک تصادفی", callback_data="music_random"),
         InlineKeyboardButton("⭐ محبوب‌ها", callback_data="music_top")],
        [InlineKeyboardButton("📚 لیست موزیک‌ها", callback_data="music_list:0")],
        [InlineKeyboardButton("❤️ علاقه‌مندی‌های من", callback_data="music_favs:0")],
    ]
    if is_admin(user_id):
        rows.append([InlineKeyboardButton("🎨 پنل مدیریت آرشیو", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


def track_keyboard(track_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❤️", callback_data=f"like:{track_id}"),
            InlineKeyboardButton("⭐ علاقه‌مندی", callback_data=f"fav:{track_id}"),
        ],
        [
            InlineKeyboardButton("🎲 تصادفی", callback_data="music_random"),
            InlineKeyboardButton("⭐ محبوب‌ها", callback_data="music_top"),
        ]
    ])


def format_track(row):
    artist = f"\n👤 {row['artist']}" if row["artist"] else ""
    cat = f"\n🎼 {row['category']}" if row["category"] else ""
    return f"🎵 {row['title']}{artist}{cat}\n📊 پخش: {row['plays']} | ❤️ {row['likes']}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "🎵 NextGuard Music\n\n"
        "موزیک را جستجو کن، ذخیره کن، آرشیو بساز و آهنگ‌های محبوب را ببین.\n\n"
        "دستورهای سریع:\n"
        "موزیک نام آهنگ\n"
        "ذخیره موزیک نام آهنگ | دسته\n"
        "لیست موزیک\n"
        "موزیک تصادفی"
    )
    await update.effective_message.reply_text(text, reply_markup=main_keyboard(user.id))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎵 راهنمای NextGuard Music\n\n"
        "🔎 جستجو:\n"
        "موزیک نام آهنگ\n"
        "/music نام آهنگ\n\n"
        "📥 ذخیره توسط ادمین:\n"
        "روی فایل صوتی ریپلای کن و بزن:\n"
        "ذخیره موزیک نام آهنگ\n"
        "یا:\n"
        "ذخیره موزیک نام آهنگ | دسته\n\n"
        "📚 لیست:\n"
        "لیست موزیک\n\n"
        "🎲 تصادفی:\n"
        "موزیک تصادفی\n\n"
        "🗑 حذف توسط ادمین:\n"
        "حذف موزیک ID\n\n"
        "👑 ادمین:\n"
        "/addadmin USER_ID\n"
        "/deladmin USER_ID"
    )
    await update.effective_message.reply_text(text)


async def send_track(update_or_query, context, row):
    chat_id = update_or_query.effective_chat.id
    con = db()
    con.execute("UPDATE tracks SET plays = plays + 1 WHERE id=?", (row["id"],))
    con.commit()
    con.close()

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_AUDIO)
    await context.bot.send_audio(
        chat_id=chat_id,
        audio=row["file_id"],
        caption=format_track(row),
        reply_markup=track_keyboard(row["id"])
    )


async def music_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    q = query.strip()
    if not q:
        await update.effective_message.reply_text("اسم آهنگ را بنویس.\nمثال:\nموزیک hello")
        return

    con = db()
    rows = con.execute(
        "SELECT * FROM tracks WHERE title LIKE ? OR artist LIKE ? OR category LIKE ? ORDER BY plays DESC, id DESC LIMIT 10",
        (f"%{q}%", f"%{q}%", f"%{q}%")
    ).fetchall()
    con.close()

    if not rows:
        await update.effective_message.reply_text("موزیکی پیدا نشد.")
        return

    if len(rows) == 1:
        await send_track(update, context, rows[0])
        return

    buttons = []
    for r in rows:
        label = f"🎵 {r['title']}"
        if r["artist"]:
            label += f" - {r['artist']}"
        buttons.append([InlineKeyboardButton(label[:60], callback_data=f"play:{r['id']}")])

    await update.effective_message.reply_text(
        "نتیجه‌های پیدا شده:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def save_music(update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str):
    msg = update.effective_message
    uid = update.effective_user.id

    if not is_admin(uid):
        await msg.reply_text("⛔ فقط مالک یا ادمین ربات می‌تواند موزیک ذخیره کند.")
        return

    if not msg.reply_to_message:
        await msg.reply_text("روی فایل صوتی ریپلای کن و بزن:\nذخیره موزیک نام آهنگ | دسته")
        return

    audio_msg = msg.reply_to_message
    audio = audio_msg.audio or audio_msg.voice or audio_msg.document
    if not audio:
        await msg.reply_text("روی فایل صوتی، ویس یا فایل موزیک ریپلای کن.")
        return

    raw = payload.strip()
    if not raw:
        raw = getattr(audio, "file_name", "") or getattr(audio, "title", "") or "بدون نام"

    parts = [p.strip() for p in raw.split("|", 1)]
    title = parts[0] or "بدون نام"
    category = parts[1] if len(parts) > 1 and parts[1] else "عمومی"

    artist = getattr(audio, "performer", "") or ""
    duration = getattr(audio, "duration", 0) or 0
    file_id = audio.file_id
    file_unique_id = getattr(audio, "file_unique_id", "")

    con = db()
    old = con.execute("SELECT id FROM tracks WHERE file_unique_id=? AND file_unique_id!=''", (file_unique_id,)).fetchone()
    if old:
        await msg.reply_text(f"این موزیک قبلاً ذخیره شده.\nID: {old['id']}")
        con.close()
        return

    cur = con.execute(
        "INSERT INTO tracks(title,artist,category,file_id,file_unique_id,duration,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (title, artist, category, file_id, file_unique_id, duration, uid, datetime.utcnow().isoformat())
    )
    con.commit()
    track_id = cur.lastrowid
    con.close()

    await msg.reply_text(f"✅ ذخیره شد.\nID: {track_id}\n🎵 {title}\n🎼 {category}")


async def list_music(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    limit = 10
    offset = page * limit
    con = db()
    rows = con.execute("SELECT id,title,artist,category,plays,likes FROM tracks ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    total = con.execute("SELECT COUNT(*) c FROM tracks").fetchone()["c"]
    con.close()

    if not rows:
        await update.effective_message.reply_text("آرشیو موزیک خالی است.")
        return

    text = f"📚 لیست موزیک‌ها\nصفحه {page+1}\n\n"
    for r in rows:
        artist = f" - {r['artist']}" if r["artist"] else ""
        text += f"{r['id']}. {r['title']}{artist}\n🎼 {r['category']} | ▶️ {r['plays']} | ❤️ {r['likes']}\n\n"

    buttons = []
    for r in rows[:5]:
        buttons.append([InlineKeyboardButton(f"▶️ {r['id']} - {r['title'][:35]}", callback_data=f"play:{r['id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"music_list:{page-1}"))
    if offset + limit < total:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"music_list:{page+1}"))
    if nav:
        buttons.append(nav)

    await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def random_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = db()
    rows = con.execute("SELECT * FROM tracks").fetchall()
    con.close()
    if not rows:
        await update.effective_message.reply_text("آرشیو موزیک خالی است.")
        return
    await send_track(update, context, random.choice(rows))


async def top_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = db()
    rows = con.execute("SELECT * FROM tracks ORDER BY plays DESC, likes DESC LIMIT 10").fetchall()
    con.close()
    if not rows:
        await update.effective_message.reply_text("هنوز موزیکی ثبت نشده.")
        return
    text = "⭐ موزیک‌های محبوب\n\n"
    buttons = []
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r['title']} | ▶️ {r['plays']} | ❤️ {r['likes']}\n"
        buttons.append([InlineKeyboardButton(f"▶️ {r['title'][:45]}", callback_data=f"play:{r['id']}")])
    await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def delete_music(update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str):
    msg = update.effective_message
    if not is_admin(update.effective_user.id):
        await msg.reply_text("⛔ فقط ادمین.")
        return
    try:
        track_id = int(payload.strip())
    except:
        await msg.reply_text("مثال:\nحذف موزیک 12")
        return

    con = db()
    con.execute("DELETE FROM favorites WHERE track_id=?", (track_id,))
    cur = con.execute("DELETE FROM tracks WHERE id=?", (track_id,))
    con.commit()
    con.close()

    if cur.rowcount:
        await msg.reply_text("🗑 موزیک حذف شد.")
    else:
        await msg.reply_text("موزیکی با این ID پیدا نشد.")


async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args:
        await update.effective_message.reply_text("/addadmin USER_ID")
        return
    try:
        uid = int(context.args[0])
    except Exception:
        await update.effective_message.reply_text("USER_ID باید عددی باشد.")
        return
    con = db()
    con.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (uid,))
    con.commit()
    con.close()
    await update.effective_message.reply_text("✅ ادمین اضافه شد.")


async def del_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args:
        await update.effective_message.reply_text("/deladmin USER_ID")
        return
    try:
        uid = int(context.args[0])
    except Exception:
        await update.effective_message.reply_text("USER_ID باید عددی باشد.")
        return
    con = db()
    con.execute("DELETE FROM admins WHERE user_id=?", (uid,))
    con.commit()
    con.close()
    await update.effective_message.reply_text("✅ ادمین حذف شد.")


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text:
        return

    text = msg.text.strip()
    low = text.lower()

    if low.startswith("/music "):
        await music_search(update, context, text.split(" ", 1)[1])
        return

    if text in ["موزیک", "اهنگ", "آهنگ", "music"]:
        await start(update, context)
        return

    if text.startswith("موزیک "):
        payload = text.replace("موزیک", "", 1).strip()
        if payload == "تصادفی":
            await random_music(update, context)
        else:
            await music_search(update, context, payload)
        return

    if text.startswith("اهنگ ") or text.startswith("آهنگ "):
        payload = text.split(" ", 1)[1].strip()
        await music_search(update, context, payload)
        return

    if text.startswith("ذخیره موزیک "):
        await save_music(update, context, text.replace("ذخیره موزیک", "", 1).strip())
        return

    if text in ["لیست موزیک", "موزیک ها", "موزیک‌ها"]:
        await list_music(update, context, 0)
        return

    if text in ["موزیک تصادفی", "اهنگ تصادفی", "آهنگ تصادفی"]:
        await random_music(update, context)
        return

    if text in ["محبوب ترین موزیک", "موزیک محبوب", "محبوب‌ها", "محبوب ها"]:
        await top_music(update, context)
        return

    if text.startswith("حذف موزیک "):
        await delete_music(update, context, text.replace("حذف موزیک", "", 1).strip())
        return


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data or ""
    await q.answer()

    if data == "music_help":
        await q.message.reply_text("برای جستجو بنویس:\nموزیک نام آهنگ")
        return

    if data == "music_random":
        await random_music(update, context)
        return

    if data == "music_top":
        await top_music(update, context)
        return

    if data.startswith("music_list:"):
        page = int(data.split(":")[1])
        await list_music(update, context, page)
        return

    if data.startswith("play:"):
        track_id = int(data.split(":")[1])
        con = db()
        row = con.execute("SELECT * FROM tracks WHERE id=?", (track_id,)).fetchone()
        con.close()
        if not row:
            await q.message.reply_text("موزیک پیدا نشد.")
            return
        await send_track(update, context, row)
        return

    if data.startswith("like:"):
        track_id = int(data.split(":")[1])
        con = db()
        con.execute("UPDATE tracks SET likes = likes + 1 WHERE id=?", (track_id,))
        con.commit()
        con.close()
        await q.answer("❤️ ثبت شد", show_alert=False)
        return

    if data.startswith("fav:"):
        track_id = int(data.split(":")[1])
        uid = q.from_user.id
        con = db()
        con.execute(
            "INSERT OR IGNORE INTO favorites(user_id,track_id,created_at) VALUES(?,?,?)",
            (uid, track_id, datetime.utcnow().isoformat())
        )
        con.commit()
        con.close()
        await q.answer("⭐ به علاقه‌مندی اضافه شد", show_alert=False)
        return

    if data.startswith("music_favs:"):
        uid = q.from_user.id
        con = db()
        rows = con.execute("""
            SELECT t.* FROM tracks t
            JOIN favorites f ON f.track_id=t.id
            WHERE f.user_id=?
            ORDER BY f.created_at DESC
            LIMIT 10
        """, (uid,)).fetchall()
        con.close()
        if not rows:
            await q.message.reply_text("علاقه‌مندی خالی است.")
            return
        buttons = [[InlineKeyboardButton(f"▶️ {r['title'][:45]}", callback_data=f"play:{r['id']}")] for r in rows]
        await q.message.reply_text("❤️ علاقه‌مندی‌های شما:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data == "admin_panel":
        if not is_admin(q.from_user.id):
            await q.message.reply_text("⛔ فقط ادمین.")
            return
        await q.message.reply_text(
            "🎨 پنل مدیریت آرشیو\n\n"
            "📥 ذخیره:\nروی موزیک ریپلای کن و بزن:\nذخیره موزیک نام آهنگ | دسته\n\n"
            "🗑 حذف:\nحذف موزیک ID\n\n"
            "📚 لیست:\nلیست موزیک"
        )
        return


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty. Set it in .env or service EnvironmentFile.")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("music", lambda u, c: music_search(u, c, " ".join(c.args))))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("deladmin", del_admin))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    log.info("NextGuard Music Bot started.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
