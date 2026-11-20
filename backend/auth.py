"""登录态：签名 token + 角色校验装饰器。

为什么不用 Cookie Session：微信小程序的 wx.request 不会自动保存/携带 Cookie，
若用 Flask session 需要前端手动搬运 Set-Cookie。这里改为登录时下发签名 token，
前端放在请求头 Authorization: Bearer <token> 中；token 内容与原方案的 session 一致：
{role: 'admin'|'volunteer', id: 管理员id/志愿者id}，由服务端密钥签名，前端无法伪造。
"""
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from core import ApiError, get_db, one

TOKEN_MAX_AGE = 7 * 24 * 3600  # 7 天
PASSWORD_METHOD = "pbkdf2:sha256:100000"


def hash_password(password):
    return generate_password_hash(password, method=PASSWORD_METHOD)


def verify_password(password_hash, password):
    try:
        return check_password_hash(password_hash, password)
    except (ValueError, TypeError):
        return False


def default_volunteer_password(student_no):
    return student_no[-6:]


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="volunteer-auth")


def issue_token(role, user_id):
    return _serializer().dumps({"role": role, "id": user_id})


def _load_user(payload):
    db = get_db()
    if payload.get("role") == "admin":
        user = one(db.execute("SELECT id, username FROM admin_user WHERE id = ?", (payload.get("id"),)))
        if user:
            return {"role": "admin", "id": user["id"], "name": user["username"]}
    elif payload.get("role") == "volunteer":
        user = one(db.execute("SELECT id, name, student_no, status FROM volunteer WHERE id = ?", (payload.get("id"),)))
        if user:
            if user["status"] != "ACTIVE":
                raise ApiError(403, "账号已停用，请联系组委会")
            return {"role": "volunteer", "id": user["id"], "name": user["name"], "student_no": user["student_no"]}
    raise ApiError(401, "请先登录")


def current_user():
    if "user" not in g:
        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.startswith("Bearer ") else ""
        if not token:
            raise ApiError(401, "请先登录")
        try:
            payload = _serializer().loads(token, max_age=TOKEN_MAX_AGE)
        except SignatureExpired:
            raise ApiError(401, "登录已过期，请重新登录") from None
        except BadSignature:
            raise ApiError(401, "请先登录") from None
        g.user = _load_user(payload)
    return g.user


def login_required(*roles):
    """@login_required() 任意已登录用户；@login_required('admin') 仅管理员。"""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if roles and user["role"] not in roles:
                raise ApiError(403, "无权操作该数据")
            return view(*args, **kwargs)

        return wrapper

    return decorator


admin_required = login_required("admin")
volunteer_required = login_required("volunteer")
