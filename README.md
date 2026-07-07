# NextGuard Music Bot

ربات موزیک مستقل تلگرام برای آرشیو، جستجو و ارسال موزیک.

## امکانات نسخه اول
- ذخیره موزیک در آرشیو با ریپلای روی فایل صوتی
- جستجوی موزیک با `موزیک نام آهنگ`
- ارسال موزیک
- لیست موزیک‌ها
- موزیک تصادفی
- محبوب‌ترین موزیک‌ها
- علاقه‌مندی کاربران
- آمار پخش و لایک
- حذف موزیک توسط ادمین
- دسته‌بندی ساده

## نصب روی VPS

```bash
cd ~
git clone YOUR_REPO_URL nextguard_music
cd nextguard_music

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

فایل `.env.example` را کپی کن:

```bash
cp .env.example .env
nano .env
```

توکن و آیدی عددی مالک را بگذار.

برای تست دستی:

```bash
export $(cat .env | xargs)
python bot.py
```

## ساخت سرویس systemd

```bash
cat >/etc/systemd/system/nextguardmusic.service <<'EOF'
[Unit]
Description=NextGuard Music Telegram Bot
After=network.target

[Service]
WorkingDirectory=/root/nextguard_music
EnvironmentFile=/root/nextguard_music/.env
ExecStart=/root/nextguard_music/venv/bin/python /root/nextguard_music/bot.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable nextguardmusic
systemctl restart nextguardmusic
systemctl status nextguardmusic --no-pager
```

## دستورها

### کاربران
```text
موزیک
موزیک نام آهنگ
اهنگ نام آهنگ
لیست موزیک
موزیک تصادفی
موزیک محبوب
```

### ادمین
روی فایل صوتی ریپلای کن:
```text
ذخیره موزیک نام آهنگ | دسته
```

حذف:
```text
حذف موزیک ID
```

مالک:
```text
/addadmin USER_ID
/deladmin USER_ID
```
