from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .db import is_admin

def home(user_id:int):
    rows = [
        [InlineKeyboardButton("🔎 جستجوی موزیک", callback_data="help_search")],
        [InlineKeyboardButton("🎲 تصادفی", callback_data="random"), InlineKeyboardButton("⭐ محبوب‌ها", callback_data="top")],
        [InlineKeyboardButton("🆕 جدیدترین", callback_data="new"), InlineKeyboardButton("🔥 ترند", callback_data="trend")],
        [InlineKeyboardButton("📚 لیست", callback_data="list:0"), InlineKeyboardButton("🎼 دسته‌بندی", callback_data="categories")],
        [InlineKeyboardButton("❤️ علاقه‌مندی‌ها", callback_data="favs"), InlineKeyboardButton("🎵 پلی‌لیست‌ها", callback_data="playlists")],
        [InlineKeyboardButton("🏆 رتبه‌بندی", callback_data="rank"), InlineKeyboardButton("🕒 تاریخچه", callback_data="history")],
    ]
    if is_admin(user_id):
        rows.append([InlineKeyboardButton("🎨 پنل مدیریت موزیک", callback_data="admin")])
    return InlineKeyboardMarkup(rows)

def track(track_id:int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ لایک", callback_data=f"like:{track_id}"),
         InlineKeyboardButton("⭐ علاقه‌مندی", callback_data=f"fav:{track_id}")],
        [InlineKeyboardButton("🎤 متن آهنگ", callback_data=f"lyrics:{track_id}"),
         InlineKeyboardButton("💿 اطلاعات", callback_data=f"info:{track_id}")],
        [InlineKeyboardButton("🎯 مشابه", callback_data=f"similar:{track_id}"),
         InlineKeyboardButton("➕ صف", callback_data=f"queue_add:{track_id}")],
        [InlineKeyboardButton("⏮", callback_data="prev"),
         InlineKeyboardButton("▶️", callback_data=f"play:{track_id}"),
         InlineKeyboardButton("⏭", callback_data="next")],
    ])

def category_buttons(categories):
    rows = [[InlineKeyboardButton(f"🎼 {c}", callback_data=f"cat:{c}:0")] for c in categories]
    return InlineKeyboardMarkup(rows)
