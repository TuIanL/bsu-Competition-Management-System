from pathlib import Path
import sqlite3

DATABASE_PATH = Path(__file__).resolve().parent.parent / "database" / "sports_volunteer.db"

def open_db():
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"找不到数据库文件：{DATABASE_PATH}")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn