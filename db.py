import sqlite3
from datetime import datetime
from .config import DB_PATH, OWNER_ID

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = connect()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS vip_users(user_id INTEGER PRIMARY KEY, created_at TEXT);

    CREATE TABLE IF NOT EXISTS tracks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT DEFAULT '',
        album TEXT DEFAULT '',
        year TEXT DEFAULT '',
        language TEXT DEFAULT 'fa',
        category TEXT DEFAULT 'عمومی',
        quality TEXT DEFAULT 'telegram',
        file_id TEXT NOT NULL,
        file_unique_id TEXT DEFAULT '',
        cover_file_id TEXT DEFAULT '',
        lyrics TEXT DEFAULT '',
        duration INTEGER DEFAULT 0,
        source TEXT DEFAULT 'telegram',
        source_url TEXT DEFAULT '',
        nsfw INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TEXT,
        plays INTEGER DEFAULT 0,
        downloads INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS favorites(
        user_id INTEGER NOT NULL,
        track_id INTEGER NOT NULL,
        created_at TEXT,
        PRIMARY KEY(user_id, track_id)
    );

    CREATE TABLE IF NOT EXISTS playlists(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        is_public INTEGER DEFAULT 0,
        share_code TEXT UNIQUE,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS playlist_items(
        playlist_id INTEGER NOT NULL,
        track_id INTEGER NOT NULL,
        position INTEGER DEFAULT 0,
        PRIMARY KEY(playlist_id, track_id)
    );

    CREATE TABLE IF NOT EXISTS play_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        track_id INTEGER,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS follows(
        user_id INTEGER NOT NULL,
        artist TEXT NOT NULL,
        created_at TEXT,
        PRIMARY KEY(user_id, artist)
    );

    CREATE TABLE IF NOT EXISTS user_points(
        user_id INTEGER PRIMARY KEY,
        points INTEGER DEFAULT 0,
        downloads INTEGER DEFAULT 0,
        plays INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS queues(
        user_id INTEGER PRIMARY KEY,
        track_ids TEXT DEFAULT '',
        position INTEGER DEFAULT 0,
        repeat INTEGER DEFAULT 0,
        shuffle INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS banned_words(word TEXT PRIMARY KEY);
    """)
    if OWNER_ID:
        con.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (OWNER_ID,))
    con.commit()
    con.close()

def is_admin(user_id:int)->bool:
    if user_id == OWNER_ID:
        return True
    con = connect()
    row = con.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    return bool(row)

def is_vip(user_id:int)->bool:
    con = connect()
    row = con.execute("SELECT 1 FROM vip_users WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    return bool(row)

def now():
    return datetime.utcnow().isoformat()
