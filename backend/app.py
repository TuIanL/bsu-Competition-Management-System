"""体育赛事志愿者调度系统 · Flask JSON API 入口。

启动：
    pip install -r backend/requirements.txt
    python backend/app.py                # 监听 0.0.0.0:5000；数据库不存在时自动建库并灌入演示数据
    python backend/app.py --reset-db     # 删除并重建演示数据库后再启动
"""
import os
import secrets
import socket
import sys
from pathlib import Path

from flask import Flask

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core import DEFAULT_DB_PATH, close_db, get_db, init_database, ok, register_error_handlers  # noqa: E402
from routes import ALL_BLUEPRINTS  # noqa: E402

SECRET_FILE = BACKEND_DIR / ".secret_key"


def _secret_key():
    """优先用环境变量；否则在本地生成一次并保存（已加入 .gitignore），重启后登录态仍有效。"""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    if not SECRET_FILE.exists():
        SECRET_FILE.write_text(secrets.token_hex(32), encoding="utf-8")
    return SECRET_FILE.read_text(encoding="utf-8").strip()


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("DATABASE_PATH", str(DEFAULT_DB_PATH)),
        JSON_AS_ASCII=False,
    )
    if config:
        app.config.update(config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = _secret_key()
    app.json.ensure_ascii = False

    if not Path(app.config["DATABASE"]).exists():
        print(f"[init] 未找到数据库，自动建库并灌入演示数据：{app.config['DATABASE']}")
        init_database(app.config["DATABASE"])

    register_error_handlers(app)
    app.teardown_appcontext(close_db)
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    @app.get("/api/health")
    def health():
        count = get_db().execute("SELECT COUNT(*) FROM volunteer").fetchone()[0]
        return ok({"status": "ok", "volunteer_count": count})

    return app


def _lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--reset-db" in sys.argv and DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()
        print("[reset] 已删除旧数据库，将重新生成演示数据")
    port = int(os.environ.get("PORT", 5000))
    application = create_app()
    print(f"[ready] 开发者工具模拟器使用：http://127.0.0.1:{port}")
    print(f"[ready] 手机真机预览使用（需同一 WiFi）：http://{_lan_ip()}:{port}")
    application.run(host="0.0.0.0", port=port, debug=False, threaded=True)
