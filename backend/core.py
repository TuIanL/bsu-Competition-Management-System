"""后端公共基础：数据库连接、统一响应、错误处理、时间工具、参数校验。"""
import importlib.util
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from flask import current_app, g, jsonify, request
from werkzeug.exceptions import HTTPException

BACKEND_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BACKEND_DIR.parent / "database"
DEFAULT_DB_PATH = DATABASE_DIR / "sports_volunteer.db"

DT_FMT = "%Y-%m-%d %H:%M:%S"
DATE_FMT = "%Y-%m-%d"

ACTIVE_ASSIGNMENT = ("ASSIGNED", "COMPLETED")  # 占用名额的调度状态


# ------------------------------------------------------------------ 响应与错误
class ApiError(Exception):
    """业务错误：抛出后由全局处理器转换为 {success:false, message}。"""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def ok(data=None, status=200):
    return jsonify({"success": True, "data": data}), status


def fail(status, message):
    return jsonify({"success": False, "message": message}), status


# 数据库约束异常 → 用户可读提示（业务层已先行校验，这里是兜底）
_INTEGRITY_MESSAGES = [
    ("assignment.shift_id, assignment.volunteer_id", "该志愿者已在本班次"),
    ("application.volunteer_id, application.shift_id", "该岗位已经报名"),
    ("volunteer.student_no", "学号已存在"),
    ("role.name", "岗位名称已存在"),
    ("admin_user.username", "用户名已存在"),
    ("start_time < end_time", "结束时间必须晚于开始时间"),
    ("required_count > 0", "需求人数必须大于 0"),
    ("FOREIGN KEY", "关联数据不存在，或该记录仍被其他数据引用"),
    ("COMPLETED assignment", "已完成的考勤记录不能修改"),
]


def integrity_message(err):
    text = str(err)
    for needle, message in _INTEGRITY_MESSAGES:
        if needle in text:
            return message
    return "数据不符合数据库约束，请检查输入"


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api_error(e):
        return fail(e.status, e.message)

    @app.errorhandler(sqlite3.IntegrityError)
    def _integrity(e):
        return fail(409, integrity_message(e))

    @app.errorhandler(HTTPException)
    def _http(e):
        messages = {404: "接口不存在", 405: "请求方法不被允许"}
        return fail(e.code, messages.get(e.code, e.description))

    @app.errorhandler(Exception)
    def _unexpected(e):
        app.logger.exception("Unhandled error")
        return fail(500, "服务器内部错误，请稍后重试")


# ------------------------------------------------------------------ 数据库
def _load_database_module(name):
    spec = importlib.util.spec_from_file_location(name, DATABASE_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init_database(path, with_seed=True):
    """建库（执行 database/schema.sql）并可选灌入演示数据。"""
    _load_database_module("init_db").init_db(path)
    if with_seed:
        conn = sqlite3.connect(str(path))
        try:
            _load_database_module("seed").seed(conn)
        finally:
            conn.close()


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"], isolation_level=None, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@contextmanager
def transaction():
    """写事务：BEGIN IMMEDIATE 先拿写锁，保证"先检查后写入"之间不会被并发请求插队。"""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def rows(cursor):
    return [dict(r) for r in cursor.fetchall()]


def one(cursor):
    r = cursor.fetchone()
    return dict(r) if r else None


def fetch_or_404(sql, params, message="记录不存在"):
    record = one(get_db().execute(sql, params))
    if record is None:
        raise ApiError(404, message)
    return record


# ------------------------------------------------------------------ 时间
def now():
    """当前时间。测试时可通过 app.config['NOW_FUNC'] 注入固定时间。"""
    func = current_app.config.get("NOW_FUNC")
    return func() if func else datetime.now()


def now_str():
    return now().strftime(DT_FMT)


def parse_dt(value):
    return datetime.strptime(value, DT_FMT)


def shift_phase(start_time, end_time, current=None):
    current = current or now_str()
    if current < start_time:
        return "upcoming"
    if current < end_time:
        return "ongoing"
    return "ended"


def minutes_between(start, end):
    return max(0, round((parse_dt(end) - parse_dt(start)).total_seconds() / 60))


# ------------------------------------------------------------------ 参数校验
def body():
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ApiError(400, "请求体必须是 JSON 对象")
    return data


def req_str(data, key, label, required=True, max_len=100):
    value = data.get(key)
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise ApiError(400, f"{label}不能为空")
        return None
    if not isinstance(value, (str, int)):
        raise ApiError(400, f"{label}格式不正确")
    value = str(value).strip()
    if len(value) > max_len:
        raise ApiError(400, f"{label}不能超过 {max_len} 个字符")
    return value


def req_int(data, key, label, required=True, minimum=None):
    value = data.get(key)
    if value is None or value == "":
        if required:
            raise ApiError(400, f"{label}不能为空")
        return None
    try:
        if isinstance(value, bool):
            raise ValueError
        number = int(value)
        if isinstance(value, float) and value != number:
            raise ValueError
    except (TypeError, ValueError):
        raise ApiError(400, f"{label}必须是整数") from None
    if minimum is not None and number < minimum:
        raise ApiError(400, f"{label}必须大于等于 {minimum}")
    return number


def req_enum(data, key, label, choices, required=True, default=None):
    value = data.get(key, default)
    if value is None:
        if required:
            raise ApiError(400, f"{label}不能为空")
        return None
    if value not in choices:
        raise ApiError(400, f"{label}只能是 {'/'.join(choices)}")
    return value


_DT_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$")


def req_datetime(data, key, label, required=True):
    """接受 YYYY-MM-DD HH:MM 或 YYYY-MM-DD HH:MM:SS，统一存为带秒格式。"""
    value = req_str(data, key, label, required=required, max_len=19)
    if value is None:
        return None
    if not _DT_RE.match(value):
        raise ApiError(400, f"{label}格式应为 YYYY-MM-DD HH:MM")
    if len(value) == 16:
        value += ":00"
    try:
        parse_dt(value)
    except ValueError:
        raise ApiError(400, f"{label}不是有效时间") from None
    return value


def req_date(data, key, label, required=True):
    value = req_str(data, key, label, required=required, max_len=10)
    if value is None:
        return None
    try:
        datetime.strptime(value, DATE_FMT)
    except ValueError:
        raise ApiError(400, f"{label}格式应为 YYYY-MM-DD") from None
    if len(value) != 10:
        raise ApiError(400, f"{label}格式应为 YYYY-MM-DD")
    return value

