"""管理端：志愿者 CRUD / 停用 / 重置密码。"""
import re

from flask import Blueprint, request

from auth import admin_required, default_volunteer_password, hash_password
from core import (ApiError, body, fetch_or_404, get_db, now_str, ok, one, req_enum, req_str, rows,
                  transaction)

bp = Blueprint("volunteers", __name__, url_prefix="/api/volunteers")

VOLUNTEER_SQL = """
SELECT v.id, v.student_no, v.name, v.phone, v.skill, v.status,
       (SELECT COUNT(*) FROM assignment a WHERE a.volunteer_id = v.id AND a.status IN ('ASSIGNED','COMPLETED'))
           AS assignment_count,
       (SELECT COUNT(*) FROM assignment a WHERE a.volunteer_id = v.id AND a.status = 'COMPLETED')
           AS completed_count
FROM volunteer v
"""

STUDENT_NO_RE = re.compile(r"^[A-Za-z0-9]{6,20}$")
PHONE_RE = re.compile(r"^[0-9+\- ]{5,20}$")


def _get(volunteer_id):
    return fetch_or_404(VOLUNTEER_SQL + " WHERE v.id = ?", (volunteer_id,), "志愿者不存在")


def _validate(data, partial):
    fields = {}
    if not partial or "student_no" in data:
        sno = req_str(data, "student_no", "学号", max_len=20)
        if not STUDENT_NO_RE.match(sno):
            raise ApiError(400, "学号应为 6–20 位字母或数字（后六位为初始密码）")
        fields["student_no"] = sno
    if not partial or "name" in data:
        fields["name"] = req_str(data, "name", "姓名", max_len=30)
    if "phone" in data:
        phone = req_str(data, "phone", "电话", required=False, max_len=20)
        if phone and not PHONE_RE.match(phone):
            raise ApiError(400, "电话格式不正确")
        fields["phone"] = phone
    if "skill" in data:
        fields["skill"] = req_str(data, "skill", "技能", required=False, max_len=100)
    if "status" in data or not partial:
        fields["status"] = req_enum(data, "status", "状态", ("ACTIVE", "INACTIVE"), default="ACTIVE")
    return fields


def _ensure_unique_student_no(db, student_no, exclude_id=None):
    dup = one(db.execute(
        "SELECT id FROM volunteer WHERE student_no = ? AND id <> ?", (student_no, exclude_id or -1)
    ))
    if dup:
        raise ApiError(409, f"学号 {student_no} 已存在")


@bp.get("")
@admin_required
def list_volunteers():
    keyword = (request.args.get("keyword") or "").strip()
    status = request.args.get("status")
    sql, params = VOLUNTEER_SQL + " WHERE 1 = 1", []
    if keyword:
        sql += " AND (v.name LIKE ? OR v.student_no LIKE ? OR v.skill LIKE ?)"
        params += [f"%{keyword}%"] * 3
    if status in ("ACTIVE", "INACTIVE"):
        sql += " AND v.status = ?"
        params.append(status)
    sql += " ORDER BY v.status, v.student_no"
    return ok(rows(get_db().execute(sql, params)))


@bp.get("/<int:volunteer_id>")
@admin_required
def get_volunteer(volunteer_id):
    return ok(_get(volunteer_id))


@bp.post("")
@admin_required
def create_volunteer():
    fields = _validate(body(), partial=False)
    with transaction() as db:
        _ensure_unique_student_no(db, fields["student_no"])
        cur = db.execute(
            "INSERT INTO volunteer (student_no, name, phone, skill, status, password_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (fields["student_no"], fields["name"], fields.get("phone"), fields.get("skill"), fields["status"],
             hash_password(default_volunteer_password(fields["student_no"]))),
        )
        new_id = cur.lastrowid
    return ok(_get(new_id), 201)


@bp.put("/<int:volunteer_id>")
@admin_required
def update_volunteer(volunteer_id):
    _get(volunteer_id)
    fields = _validate(body(), partial=True)
    if not fields:
        raise ApiError(400, "没有需要修改的字段")
    with transaction() as db:
        if "student_no" in fields:
            _ensure_unique_student_no(db, fields["student_no"], volunteer_id)
        sets = ", ".join(f"{k} = ?" for k in fields)
        db.execute(f"UPDATE volunteer SET {sets} WHERE id = ?", (*fields.values(), volunteer_id))
    result = _get(volunteer_id)
    # 停用时提醒：该志愿者仍有未开始的班次，管理员可到调度页取消
    result["future_assignment_count"] = get_db().execute(
        """SELECT COUNT(*) FROM assignment a JOIN shift s ON s.id = a.shift_id
           WHERE a.volunteer_id = ? AND a.status = 'ASSIGNED' AND s.end_time > ?""",
        (volunteer_id, now_str()),
    ).fetchone()[0]
    return ok(result)


@bp.post("/<int:volunteer_id>/reset-password")
@admin_required
def reset_password(volunteer_id):
    vol = _get(volunteer_id)
    with transaction() as db:
        db.execute(
            "UPDATE volunteer SET password_hash = ? WHERE id = ?",
            (hash_password(default_volunteer_password(vol["student_no"])), volunteer_id),
        )
    return ok({"message": f"密码已重置为学号后六位（{default_volunteer_password(vol['student_no'])}）"})
