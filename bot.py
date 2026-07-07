import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes, filters
from telegram import InlineQueryResultArticle, InputTextMessageContent

from .config import BOT_TOKEN, OWNER_ID, BOT_USERNAME
from .db import init_db, connect, is_admin, is_vip, now
from .keyboards import home, track as track_kb, category_buttons
from . import services as sv
from .downloader import download_online

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("NextGuardMusic")

def fmt_track(r):
    parts = [f"🎵 {r['title']}"]
    if r["artist"]: parts.append(f"👤 {r['artist']}")
    if r["album"]: parts.append(f"💿 {r['album']}")
    if r["year"]: parts.append(f"📅 {r['year']}")
    if r["category"]: parts.append(f"🎼 {r['category']}")
    if r["duration"]: parts.append(f"⏱ {r['duration']}s")
    parts.append(f"📊 پخش: {r['plays']} | دانلود: {r['downloads']} | ❤️ {r['likes']}")
    return "\n".join(parts)

async def send_track(update: Update, context: ContextTypes.DEFAULT_TYPE, r):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else 0
    sv.record_play(user_id, r["id"])
    await context.bot.send_chat_action(chat_id, ChatAction.UPLOAD_AUDIO)
    await context.bot.send_audio(chat_id, r["file_id"], caption=fmt_track(r), reply_markup=track_kb(r["id"]))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🎵 NextGuard Music\n\n"
        "به موزیک پلیر حرفه‌ای نکست گارد خوش آمدی.\n\n"
        "برای جستجو بنویس:\n"
        "موزیک نام آهنگ",
        reply_markup=home(update.effective_user.id)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🎵 راهنما\n\n"
        "موزیک نام آهنگ\n"
        "آهنگ نام آهنگ\n"
        "لیست موزیک\n"
        "موزیک تصادفی\n"
        "موزیک محبوب\n"
        "جدیدترین موزیک\n"
        "دسته بندی موزیک\n\n"
        "ادمین:\n"
        "ذخیره موزیک عنوان | دسته | خواننده | آلبوم | سال | زبان\n"
        "متن آهنگ ID متن\n"
        "حذف موزیک ID"
    )

async def cmd_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await search_and_send(update, context, " ".join(context.args))

async def search_and_send(update, context, q):
    if not q.strip():
        await update.effective_message.reply_text("اسم آهنگ را بنویس.")
        return
    rows = sv.search_tracks(q, 10)
    if not rows:
        await update.effective_message.reply_text("موزیکی پیدا نشد.")
        return
    if len(rows) == 1:
        await send_track(update, context, rows[0])
        return
    buttons = [[InlineKeyboardButton(f"▶️ {r['title'][:50]}", callback_data=f"play:{r['id']}")] for r in rows]
    await update.effective_message.reply_text("نتیجه‌ها:", reply_markup=InlineKeyboardMarkup(buttons))

async def save_music(update, context, payload):
    msg = update.effective_message
    if not is_admin(update.effective_user.id):
        await msg.reply_text("⛔ فقط ادمین.")
        return
    if not msg.reply_to_message:
        await msg.reply_text("روی فایل صوتی ریپلای کن و بزن:\nذخیره موزیک عنوان | دسته | خواننده | آلبوم | سال | زبان")
        return

    m = msg.reply_to_message
    audio = m.audio or m.voice or m.document
    if not audio:
        await msg.reply_text("روی فایل صوتی/ویس/فایل موزیک ریپلای کن.")
        return

    parts = [p.strip() for p in payload.split("|")]
    title = parts[0] if len(parts)>0 and parts[0] else getattr(audio, "file_name", "") or getattr(audio, "title", "") or "بدون نام"
    category = parts[1] if len(parts)>1 and parts[1] else "عمومی"
    artist = parts[2] if len(parts)>2 else getattr(audio, "performer", "") or ""
    album = parts[3] if len(parts)>3 else ""
    year = parts[4] if len(parts)>4 else ""
    language = parts[5] if len(parts)>5 else "fa"
    duration = getattr(audio, "duration", 0) or 0

    con = connect()
    old = con.execute("SELECT id FROM tracks WHERE file_unique_id=? AND file_unique_id!=''", (getattr(audio, "file_unique_id", ""),)).fetchone()
    if old:
        con.close()
        await msg.reply_text(f"قبلاً ذخیره شده. ID: {old['id']}")
        return
    cur = con.execute("""
        INSERT INTO tracks(title,artist,album,year,language,category,file_id,file_unique_id,duration,created_by,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (title, artist, album, year, language, category, audio.file_id, getattr(audio, "file_unique_id", ""), duration, update.effective_user.id, now()))
    con.commit()
    tid = cur.lastrowid
    con.close()
    await msg.reply_text(f"✅ ذخیره شد\nID: {tid}\n🎵 {title}")

async def list_music(update, context, page=0):
    rows, total = sv.list_tracks(page)
    if not rows:
        await update.effective_message.reply_text("آرشیو موزیک خالی است.")
        return
    text = f"📚 لیست موزیک‌ها | صفحه {page+1}\n\n"
    buttons = []
    for r in rows:
        text += f"{r['id']}. {r['title']} | {r['category']} | ▶️ {r['plays']}\n"
        buttons.append([InlineKeyboardButton(f"▶️ {r['id']} - {r['title'][:35]}", callback_data=f"play:{r['id']}")])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"list:{page-1}"))
    if (page+1)*10 < total: nav.append(InlineKeyboardButton("➡️", callback_data=f"list:{page+1}"))
    if nav: buttons.append(nav)
    await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def show_rows(update, title, rows):
    if not rows:
        await update.effective_message.reply_text("موردی پیدا نشد.")
        return
    text = title + "\n\n"
    buttons = []
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r['title']} | ▶️ {r['plays']} | ❤️ {r['likes']}\n"
        buttons.append([InlineKeyboardButton(f"▶️ {r['title'][:45]}", callback_data=f"play:{r['id']}")])
    await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def delete_music(update, context, payload):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین.")
        return
    try: tid = int(payload.strip())
    except: 
        await update.effective_message.reply_text("مثال: حذف موزیک 12")
        return
    con = connect()
    con.execute("DELETE FROM favorites WHERE track_id=?", (tid,))
    con.execute("DELETE FROM playlist_items WHERE track_id=?", (tid,))
    cur = con.execute("DELETE FROM tracks WHERE id=?", (tid,))
    con.commit(); con.close()
    await update.effective_message.reply_text("🗑 حذف شد." if cur.rowcount else "ID پیدا نشد.")

async def set_lyrics(update, context, payload):
    if not is_admin(update.effective_user.id): return
    try:
        tid_s, lyrics = payload.split(" ", 1)
        tid = int(tid_s)
    except:
        await update.effective_message.reply_text("مثال:\nمتن آهنگ 12 متن آهنگ...")
        return
    con = connect(); con.execute("UPDATE tracks SET lyrics=? WHERE id=?", (lyrics, tid)); con.commit(); con.close()
    await update.effective_message.reply_text("🎤 متن آهنگ ذخیره شد.")

async def set_cover(update, context, payload):
    if not is_admin(update.effective_user.id): return
    if not update.effective_message.reply_to_message or not update.effective_message.reply_to_message.photo:
        await update.effective_message.reply_text("روی عکس کاور ریپلای کن و بزن: کاور موزیک ID")
        return
    try: tid = int(payload.strip())
    except:
        await update.effective_message.reply_text("مثال: کاور موزیک 12")
        return
    fid = update.effective_message.reply_to_message.photo[-1].file_id
    con = connect(); con.execute("UPDATE tracks SET cover_file_id=? WHERE id=?", (fid, tid)); con.commit(); con.close()
    await update.effective_message.reply_text("💿 کاور ذخیره شد.")

async def admin_cmd(update, context, add=True):
    if update.effective_user.id != OWNER_ID: return
    if not context.args: 
        await update.effective_message.reply_text("/addadmin USER_ID")
        return
    uid = int(context.args[0])
    con = connect()
    if add: con.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (uid,))
    else: con.execute("DELETE FROM admins WHERE user_id=?", (uid,))
    con.commit(); con.close()
    await update.effective_message.reply_text("✅ انجام شد.")

async def vip_cmd(update, context, add=True):
    if not is_admin(update.effective_user.id): return
    if not context.args: return
    uid = int(context.args[0])
    con = connect()
    if add: con.execute("INSERT OR IGNORE INTO vip_users(user_id,created_at) VALUES(?,?)", (uid, now()))
    else: con.execute("DELETE FROM vip_users WHERE user_id=?", (uid,))
    con.commit(); con.close()
    await update.effective_message.reply_text("✅ انجام شد.")

async def text_router(update, context):
    msg = update.effective_message
    if not msg or not msg.text: return
    text = msg.text.strip()

    if sv.blocked_by_filter(text):
        return

    if text in ["موزیک", "music", "🎵 NextGuard Music"]:
        await start(update, context); return
    if text.startswith("موزیک "):
        q = text.replace("موزیک", "", 1).strip()
        if q == "تصادفی": await random_track(update, context)
        else: await search_and_send(update, context, q)
        return
    if text.startswith("آهنگ ") or text.startswith("اهنگ "):
        await search_and_send(update, context, text.split(" ",1)[1]); return
    if text.startswith("ذخیره موزیک "):
        await save_music(update, context, text.replace("ذخیره موزیک", "", 1).strip()); return
    if text in ["لیست موزیک", "موزیک‌ها", "موزیک ها"]:
        await list_music(update, context); return
    if text in ["موزیک تصادفی", "آهنگ تصادفی", "اهنگ تصادفی"]:
        await random_track(update, context); return
    if text in ["موزیک محبوب", "محبوب‌ها", "محبوب ها", "محبوب ترین موزیک"]:
        await show_rows(update, "⭐ محبوب‌ترین موزیک‌ها", sv.top_tracks()); return
    if text in ["جدیدترین موزیک", "موزیک جدید"]:
        await show_rows(update, "🆕 جدیدترین موزیک‌ها", sv.new_tracks()); return
    if text in ["ترند موزیک", "موزیک ترند"]:
        await show_rows(update, "🔥 ترند روز", sv.top_tracks()); return
    if text in ["دسته بندی موزیک", "دسته‌بندی موزیک"]:
        cats = sv.categories()
        await msg.reply_text("🎼 دسته‌بندی‌ها", reply_markup=category_buttons(cats) if cats else None); return
    if text.startswith("حذف موزیک "):
        await delete_music(update, context, text.replace("حذف موزیک", "", 1).strip()); return
    if text.startswith("متن آهنگ "):
        await set_lyrics(update, context, text.replace("متن آهنگ", "", 1).strip()); return
    if text.startswith("کاور موزیک "):
        await set_cover(update, context, text.replace("کاور موزیک", "", 1).strip()); return
    if text.startswith("پلی لیست بساز ") or text.startswith("پلی‌لیست بساز "):
        name = text.split("بساز",1)[1].strip()
        pid, code = sv.make_playlist(update.effective_user.id, name)
        await msg.reply_text(f"🎵 پلی‌لیست ساخته شد.\nID: {pid}\nکد اشتراک: {code}"); return
    if text == "پلی لیست من" or text == "پلی‌لیست من":
        rows = sv.user_playlists(update.effective_user.id)
        await msg.reply_text("\n".join([f"{r['id']}. {r['name']} | {r['share_code']}" for r in rows]) or "پلی‌لیستی نداری."); return
    if text == "تاریخچه موزیک":
        await show_rows(update, "🕒 تاریخچه", sv.history(update.effective_user.id)); return
    if text == "رتبه موزیک":
        rows = sv.rank()
        txt = "🏆 رتبه‌بندی کاربران\n\n" + "\n".join([f"{i}. {r['user_id']} | امتیاز: {r['points']} | دانلود: {r['downloads']}" for i,r in enumerate(rows,1)])
        await msg.reply_text(txt); return

async def random_track(update, context):
    r = sv.random_track()
    if not r:
        await update.effective_message.reply_text("آرشیو خالی است.")
        return
    await send_track(update, context, r)

async def callbacks(update, context):
    q = update.callback_query
    data = q.data or ""
    await q.answer()

    if data == "help_search":
        await q.message.reply_text("برای جستجو بنویس:\nموزیک نام آهنگ"); return
    if data == "random":
        await random_track(update, context); return
    if data == "top":
        await show_rows(update, "⭐ محبوب‌ترین موزیک‌ها", sv.top_tracks()); return
    if data == "new":
        await show_rows(update, "🆕 جدیدترین موزیک‌ها", sv.new_tracks()); return
    if data == "trend":
        await show_rows(update, "🔥 ترند روز", sv.top_tracks()); return
    if data.startswith("list:"):
        await list_music(update, context, int(data.split(":")[1])); return
    if data == "categories":
        cats = sv.categories()
        await q.message.reply_text("🎼 دسته‌بندی‌ها", reply_markup=category_buttons(cats) if cats else None); return
    if data.startswith("cat:"):
        _, cat, page = data.split(":", 2)
        rows = sv.search_tracks(cat, 10)
        await show_rows(update, f"🎼 {cat}", rows); return
    if data.startswith("play:"):
        r = sv.get_track(int(data.split(":")[1]))
        if r: await send_track(update, context, r)
        return
    if data.startswith("like:"):
        sv.like(int(data.split(":")[1])); await q.answer("❤️ ثبت شد"); return
    if data.startswith("fav:"):
        sv.fav(q.from_user.id, int(data.split(":")[1])); await q.answer("⭐ ذخیره شد"); return
    if data == "favs":
        await show_rows(update, "❤️ علاقه‌مندی‌ها", sv.favs(q.from_user.id)); return
    if data == "history":
        await show_rows(update, "🕒 تاریخچه", sv.history(q.from_user.id)); return
    if data == "rank":
        rows = sv.rank()
        txt = "🏆 رتبه‌بندی کاربران\n\n" + "\n".join([f"{i}. {r['user_id']} | امتیاز: {r['points']}" for i,r in enumerate(rows,1)])
        await q.message.reply_text(txt or "خالی است."); return
    if data == "playlists":
        rows = sv.user_playlists(q.from_user.id)
        await q.message.reply_text("\n".join([f"{r['id']}. {r['name']} | {r['share_code']}" for r in rows]) or "پلی‌لیستی نداری."); return
    if data.startswith("lyrics:"):
        r = sv.get_track(int(data.split(":")[1]))
        await q.message.reply_text(r["lyrics"] or "متن آهنگ ثبت نشده."); return
    if data.startswith("info:"):
        r = sv.get_track(int(data.split(":")[1]))
        if r:
            await q.message.reply_text(fmt_track(r))
            if r["cover_file_id"]:
                await q.message.reply_photo(r["cover_file_id"], caption="💿 کاور آلبوم")
        return
    if data.startswith("similar:"):
        await show_rows(update, "🎯 موزیک‌های مشابه", sv.similar(int(data.split(":")[1]))); return
    if data.startswith("queue_add:"):
        sv.queue_add(q.from_user.id, int(data.split(":")[1])); await q.answer("➕ به صف اضافه شد"); return
    if data in ["next","prev"]:
        ids, pos, rep, sh = sv.queue_get(q.from_user.id)
        if not ids:
            await q.message.reply_text("صف خالی است."); return
        pos = (pos + (1 if data=="next" else -1)) % len(ids)
        sv.queue_set(q.from_user.id, ids, pos, rep, sh)
        r = sv.get_track(ids[pos])
        if r: await send_track(update, context, r)
        return
    if data == "admin":
        await q.message.reply_text("🎨 پنل مدیریت\n\nذخیره موزیک عنوان | دسته | خواننده | آلبوم | سال | زبان\nمتن آهنگ ID متن\nکاور موزیک ID\nحذف موزیک ID"); return

async def inline_query(update, context):
    q = update.inline_query.query.strip()
    if not q: return
    rows = sv.search_tracks(q, 10)
    results = []
    for r in rows:
        results.append(InlineQueryResultArticle(
            id=str(r["id"]),
            title=r["title"],
            description=f"{r['artist']} | {r['category']}",
            input_message_content=InputTextMessageContent(f"موزیک {r['title']}")
        ))
    await update.inline_query.answer(results, cache_time=5)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty")
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("music", cmd_music))
    app.add_handler(CommandHandler("addadmin", lambda u,c: admin_cmd(u,c,True)))
    app.add_handler(CommandHandler("deladmin", lambda u,c: admin_cmd(u,c,False)))
    app.add_handler(CommandHandler("vip", lambda u,c: vip_cmd(u,c,True)))
    app.add_handler(CommandHandler("unvip", lambda u,c: vip_cmd(u,c,False)))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    log.info("NextGuard Music is running")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
