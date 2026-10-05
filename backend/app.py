from flask import Flask
from db import open_db

app = Flask(__name__)

@app.get("/api/health")
def health():
    conn = open_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM volunteer").fetchone()[0]
    finally:
        conn.close()

    return {"success": True, "data": {
        "status": "ok",
        "volunteer_count": count
    }}

if __name__ == "__main__":
    app.run(port=5000)