import random, json, uuid
from .db import connect, now

BAD_WORDS_DEFAULT = set()

def search_tracks(q, limit=10):
    con = connect()
    rows = con.execute("""
        SELECT * FROM tracks
        WHERE title LIKE ? OR artist LIKE ? OR album LIKE ? OR category LIKE ? OR lyrics LIKE ?
        ORDER BY plays DESC, likes DESC, id DESC
        LIMIT ?
    """, (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", limit)).fetchall()
    con.close()
    return rows

def get_track(track_id):
    con = connect()
    row = con.execute("SELECT * FROM tracks WHERE id=?", (track_id,)).fetchone()
    con.close()
    return row

def list_tracks(page=0, limit=10):
    con = connect()
    rows = con.execute("SELECT * FROM tracks ORDER BY id DESC LIMIT ? OFFSET ?", (limit, page*limit)).fetchall()
    total = con.execute("SELECT COUNT(*) c FROM tracks").fetchone()["c"]
    con.close()
    return rows, total

def random_track(category=None):
    con = connect()
    if category:
        rows = con.execute("SELECT * FROM tracks WHERE category=?", (category,)).fetchall()
    else:
        rows = con.execute("SELECT * FROM tracks").fetchall()
    con.close()
    return random.choice(rows) if rows else None

def top_tracks(limit=10):
    con = connect()
    rows = con.execute("SELECT * FROM tracks ORDER BY downloads DESC, plays DESC, likes DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return rows

def new_tracks(limit=10):
    con = connect()
    rows = con.execute("SELECT * FROM tracks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return rows

def categories():
    con = connect()
    rows = con.execute("SELECT DISTINCT category FROM tracks WHERE category!='' ORDER BY category").fetchall()
    con.close()
    return [r["category"] for r in rows]

def add_points(user_id, plays=0, downloads=0, points=0):
    con = connect()
    con.execute("""
        INSERT INTO user_points(user_id,points,downloads,plays) VALUES(?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
          points=points+excluded.points,
          downloads=downloads+excluded.downloads,
          plays=plays+excluded.plays
    """, (user_id, points, downloads, plays))
    con.commit(); con.close()

def record_play(user_id, track_id):
    con = connect()
    con.execute("UPDATE tracks SET plays=plays+1, downloads=downloads+1 WHERE id=?", (track_id,))
    con.execute("INSERT INTO play_history(user_id,track_id,created_at) VALUES(?,?,?)", (user_id, track_id, now()))
    con.commit(); con.close()
    add_points(user_id, plays=1, downloads=1, points=1)

def like(track_id):
    con = connect()
    con.execute("UPDATE tracks SET likes=likes+1 WHERE id=?", (track_id,))
    con.commit(); con.close()

def fav(user_id, track_id):
    con = connect()
    con.execute("INSERT OR IGNORE INTO favorites(user_id,track_id,created_at) VALUES(?,?,?)", (user_id, track_id, now()))
    con.commit(); con.close()

def favs(user_id):
    con = connect()
    rows = con.execute("""
        SELECT t.* FROM tracks t JOIN favorites f ON f.track_id=t.id
        WHERE f.user_id=? ORDER BY f.created_at DESC LIMIT 20
    """, (user_id,)).fetchall()
    con.close()
    return rows

def history(user_id):
    con = connect()
    rows = con.execute("""
        SELECT t.* FROM tracks t JOIN play_history h ON h.track_id=t.id
        WHERE h.user_id=? ORDER BY h.id DESC LIMIT 20
    """, (user_id,)).fetchall()
    con.close()
    return rows

def rank():
    con = connect()
    rows = con.execute("SELECT * FROM user_points ORDER BY points DESC LIMIT 10").fetchall()
    con.close()
    return rows

def similar(track_id):
    tr = get_track(track_id)
    if not tr:
        return []
    con = connect()
    rows = con.execute("""
        SELECT * FROM tracks WHERE id!=? AND (category=? OR artist=? OR language=?)
        ORDER BY plays DESC LIMIT 10
    """, (track_id, tr["category"], tr["artist"], tr["language"])).fetchall()
    con.close()
    return rows

def artist_tracks(artist):
    con = connect()
    rows = con.execute("SELECT * FROM tracks WHERE artist LIKE ? ORDER BY year DESC, id DESC LIMIT 20", (f"%{artist}%",)).fetchall()
    con.close()
    return rows

def make_playlist(user_id, name, is_public=0):
    code = uuid.uuid4().hex[:8]
    con = connect()
    cur = con.execute("INSERT INTO playlists(user_id,name,is_public,share_code,created_at) VALUES(?,?,?,?,?)",
                      (user_id, name, is_public, code, now()))
    con.commit()
    pid = cur.lastrowid
    con.close()
    return pid, code

def add_to_playlist(playlist_id, track_id):
    con = connect()
    pos = con.execute("SELECT COUNT(*) c FROM playlist_items WHERE playlist_id=?", (playlist_id,)).fetchone()["c"]
    con.execute("INSERT OR IGNORE INTO playlist_items(playlist_id,track_id,position) VALUES(?,?,?)", (playlist_id, track_id, pos+1))
    con.commit(); con.close()

def user_playlists(user_id):
    con = connect()
    rows = con.execute("SELECT * FROM playlists WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    con.close()
    return rows

def queue_set(user_id, ids, position=0, repeat=0, shuffle=0):
    con = connect()
    con.execute("""
    INSERT INTO queues(user_id,track_ids,position,repeat,shuffle) VALUES(?,?,?,?,?)
    ON CONFLICT(user_id) DO UPDATE SET track_ids=excluded.track_ids, position=excluded.position, repeat=excluded.repeat, shuffle=excluded.shuffle
    """, (user_id, ",".join(map(str, ids)), position, repeat, shuffle))
    con.commit(); con.close()

def queue_get(user_id):
    con = connect()
    row = con.execute("SELECT * FROM queues WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    if not row:
        return [], 0, 0, 0
    ids = [int(x) for x in row["track_ids"].split(",") if x.strip().isdigit()]
    return ids, row["position"], row["repeat"], row["shuffle"]

def queue_add(user_id, track_id):
    ids, pos, rep, sh = queue_get(user_id)
    ids.append(track_id)
    queue_set(user_id, ids, pos, rep, sh)

def blocked_by_filter(text):
    con = connect()
    words = [r["word"] for r in con.execute("SELECT word FROM banned_words").fetchall()]
    con.close()
    low = (text or "").lower()
    return any(w and w.lower() in low for w in words)
