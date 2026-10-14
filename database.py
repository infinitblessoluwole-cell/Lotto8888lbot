import sqlite3
from contextlib import contextmanager
from datetime import date
from typing import Optional

DB_PATH = "vocabulary.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                daily_word_index INTEGER DEFAULT 0,
                last_daily_date TEXT
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                translation TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, word)
            );

            CREATE TABLE IF NOT EXISTS learned (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                translation TEXT NOT NULL,
                learned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                review_count INTEGER DEFAULT 0,
                UNIQUE(user_id, word)
            );

            CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
            CREATE INDEX IF NOT EXISTS idx_learned_user ON learned(user_id);
        """)

def get_or_create_user(user_id: int) -> sqlite3.Row:
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

def update_daily_progress(user_id: int, word_index: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET daily_word_index = ?, last_daily_date = ? WHERE user_id = ?",
            (word_index, date.today().isoformat(), user_id)
        )

def add_favorite(user_id: int, word: str, translation: str) -> bool:
    """Returns True if inserted, False if already exists."""
    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO favorites (user_id, word, translation) VALUES (?, ?, ?)",
                (user_id, word, translation)
            )
            return True
        except sqlite3.IntegrityError:
            return False

def get_favorites(user_id: int) -> list:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT word, translation FROM favorites WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def add_learned(user_id: int, word: str, translation: str):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO learned (user_id, word, translation) 
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, word) DO UPDATE SET
               review_count = review_count + 1""",
            (user_id, word, translation)
        )

def get_learned(user_id: int, limit: int = 10) -> list:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT word, translation, review_count FROM learned WHERE user_id = ? ORDER BY learned_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

def get_daily_word(user_id: int, words: list) -> tuple:
    """Return (word_dict, new_index) for today's word."""
    user = get_or_create_user(user_id)
    today = date.today().isoformat()
    
    if user["last_daily_date"] == today:
        idx = user["daily_word_index"]
    else:
        idx = (user["daily_word_index"] + 1) % len(words)
        update_daily_progress(user_id, idx)
    
    return words[idx], idx
