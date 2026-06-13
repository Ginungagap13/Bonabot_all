import sqlite3
from pathlib import Path
from typing import Optional, List, Tuple

DB_PATH = Path("bot.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                photo_file_id TEXT,
                code TEXT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                winner_user_id INTEGER,
                winner_username TEXT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

def add_message(chat_id: int, user_id: int, username: str,
                photo_file_id: str, code: str):
    with get_conn() as db:
        db.execute("""
            INSERT INTO messages (chat_id, user_id, username, photo_file_id, code)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, username, photo_file_id, code))

def list_messages() -> List[sqlite3.Row]:
    with get_conn() as db:
        return list(db.execute("SELECT * FROM messages ORDER BY ts DESC"))

def add_winner(message_id: int, winner_user_id: int, winner_username: str):
    with get_conn() as db:
        db.execute("""
            INSERT INTO winners (message_id, winner_user_id, winner_username)
            VALUES (?, ?, ?)
        """, (message_id, winner_user_id, winner_username))

def list_winners() -> List[sqlite3.Row]:
    with get_conn() as db:
        return list(db.execute("SELECT * FROM winners ORDER BY ts DESC"))
