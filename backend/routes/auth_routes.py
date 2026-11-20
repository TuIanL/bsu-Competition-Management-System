"""统一登录 / 退出 / 当前用户 / 修改密码（管理员与志愿者共用）。"""
from flask import Blueprint

from auth import (current_user, default_volunteer_password, hash_password, issue_token, login_required,
                  verify_password)
from core import ApiError, body, get_db, ok, one, req_str, transaction

bp = Blueprint("auth", __name__, url_prefix="/api")


@bp.post("/login")
def login():
    data = body()
    username = req_str(data, "username", "账号")
    password = req_str(data, "password", "密码")
    db = get_db()

    # 1) 先查管理员表
    admin = one(db.execute("SELECT id, username, password_hash FROM admin_user WHERE username = ?", (username,)))
    if admin and verify_password(admin["password_hash"], password):
        return ok({
            "token": issue_token("admin", admin["id"]),
            "role": "admin",
            "id": admin["id"],
            "name": admin["username"],
            "must_change_password": False,
        })

    # 2) 再查志愿者表（学号登录）
    vol = one(db.execute(
        "SELECT id, name, student_no, status, password_hash FROM volunteer WHERE student_no = ?", (username,)
    ))
    if vol and verify_password(vol["password_hash"], password):
        if vol["status"] != "ACTIVE":
            raise ApiError(403, "账号已停用，请联系组委会")
        return ok({
            "token": issue_token("volunteer", vol["id"]),
            "role": "volunteer",
            "id": vol["id"],
            "name": vol["name"],
            "student_no": vol["student_no"],
            # 仍在使用初始密码（学号后六位）时提示修改
            "must_change_password": password == default_volunteer_password(vol["student_no"]),
        })

    raise ApiError(401, "账号或密码错误")


@bp.post("/logout")
def logout():
    # token 为无状态签名，前端清除本地 token 即完成退出
    return ok(None)


@bp.get("/me")
@login_required()
def me():
    return ok(current_user())


@bp.post("/password")
@login_required()
def change_password():
    data = body()
    old = req_str(data, "old_password", "原密码")
    new = req_str(data, "new_password", "新密码", max_len=32)
    if len(new) < 6:
        raise ApiError(400, "新密码至少 6 位")
    if new == old:
        raise ApiError(400, "新密码不能与原密码相同")
    user = current_user()
    table = "admin_user" if user["role"] == "admin" else "volunteer"
    with transaction() as db:
        row = one(db.execute(f"SELECT password_hash FROM {table} WHERE id = ?", (user["id"],)))
        if not verify_password(row["password_hash"], old):
            raise ApiError(400, "原密码不正确")
        db.execute(f"UPDATE {table} SET password_hash = ? WHERE id = ?", (hash_password(new), user["id"]))
    return ok(None)
