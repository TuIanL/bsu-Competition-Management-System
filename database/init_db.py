"""一键建库：执行 schema.sql，生成 sports_volunteer.db。

用法（在任意目录均可）：
    python database/init_db.py              # 默认生成 database/sports_volunteer.db
    python database/init_db.py other.db     # 指定数据库文件
"""
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE / "sports_volunteer.db"
SCHEMA = HERE / "schema.sql"


def init_db(db_path=DEFAULT_DB):
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        conn.commit()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [t[0] for t in tables]
    finally:
        conn.close()


if __name__ == "__main__":
    # Windows 的 Git Bash / 管道输出默认不是 UTF-8，统一一下避免中文乱码或报错
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    tables = init_db(path)
    print(f"数据库初始化成功：{path}")
    print("当前表：", tables)
