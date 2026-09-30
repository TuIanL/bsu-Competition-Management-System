import sqlite3

conn = sqlite3.connect("sports_volunteer.db")
conn.execute("PRAGMA foreign_keys = ON")

with open("schema.sql", "r", encoding="utf-8") as f:
    sql = f.read()

conn.executescript(sql)
conn.commit()
print("数据库初始化成功")

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print("当前表：", [t[0] for t in tables])

conn.close()