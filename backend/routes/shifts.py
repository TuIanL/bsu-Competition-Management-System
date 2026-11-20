"""管理端：班次维护、名单、缺口、报名参考、候选人。"""
from flask import Blueprint, request

from auth import admin_required
from core import (ApiError, body, fetch_or_404, get_db, now_str, ok, req_datetime, req_int, req_str, rows,
                  shift_phase, transaction)
from rules import SHIFT_DETAIL_SQL, describe_shift, find_conflict, get_shift, skill_match

bp = Blueprint("shifts", __name__, url_prefix="/api/shifts")

LIST_SQL = SHIFT_DETAIL_SQL.replace(
    "v.assigned_count, v.remaining_count",
    "v.assigned_count, v.remaining_count, "
    "(SELECT COUNT(*) FROM application ap WHERE ap.shift_id = s.id AND ap.status = 'PENDING') AS pending_applications",
)


def _decorate(shift, current):
    shift["phase"] = shift_phase(shift["start_time"], shift["end_time"], current)
    shift["is_full"] = shift["remaining_count"] <= 0
    return shift


@bp.get("")
@admin_required
def list_shifts():
    sql, params = LIST_SQL + " WHERE 1 = 1", []
    event_id = request.args.get("event_id", type=int)
    if event_id:
        sql += " AND s.event_id = ?"
        params.append(event_id)
    scope = request.args.get("scope", "all")
    current = now_str()
    if scope == "active":  # 未结束（进行中 + 未开始）
        sql += " AND s.end_time > ?"
        params.append(current)
    elif scope == "ended":
        sql += " AND s.end_time <= ?"
        params.append(current)
    sql += " ORDER BY s.start_time DESC" if scope == "ended" else " ORDER BY s.start_time"
    return ok([_decorate(s, current) for s in rows(get_db().execute(sql, params))])


@bp.get("/<int:shift_id>")
@admin_required
def get_one(shift_id):
    shift = fetch_or_404(LIST_SQL + " WHERE s.id = ?", (shift_id,), "班次不存在")
    return ok(_decorate(shift, now_str()))


def _fields(data, partial, original=None):
    f = {}
    if not partial or "event_id" in data:
        f["event_id"] = req_int(data, "event_id", "赛事")
        fetch_or_404("SELECT id FROM event WHERE id = ?", (f["event_id"],), "所选赛事不存在")
    if not partial or "role_id" in data:
        f["role_id"] = req_int(data, "role_id", "岗位")
        fetch_or_404("SELECT id FROM role WHERE id = ?", (f["role_id"],), "所选岗位不存在")
    if not partial or "start_time" in data:
        f["start_time"] = req_datetime(data, "start_time", "开始时间")
    if not partial or "end_time" in data:
        f["end_time"] = req_datetime(data, "end_time", "结束时间")
    if not partial or "required_count" in data:
        f["required_count"] = req_int(data, "required_count", "需求人数", minimum=1)
        if f["required_count"] > 500:
            raise ApiError(400, "需求人数不能超过 500")
    if "note" in data:
        f["note"] = req_str(data, "note", "备注", required=False, max_len=100)
    start = f.get("start_time", original and original["start_time"])
    end = f.get("end_time", original and original["end_time"])
    if start and end and start >= end:
        raise ApiError(400, "结束时间必须晚于开始时间")
    return f


@bp.post("")
@admin_required
def create_shift():
    f = _fields(body(), partial=False)
    with transaction() as db:
        new_id = db.execute(
            "INSERT INTO shift (event_id, role_id, start_time, end_time, required_count, note) VALUES (?, ?, ?, ?, ?, ?)",
            (f["event_id"], f["role_id"], f["start_time"], f["end_time"], f["required_count"], f.get("note")),
        ).lastrowid
    return ok(_decorate(fetch_or_404(LIST_SQL + " WHERE s.id = ?", (new_id,)), now_str()), 201)


@bp.put("/<int:shift_id>")
@admin_required
def update_shift(shift_id):
    original = get_shift(shift_id)
    f = _fields(body(), partial=True, original=original)
    if not f:
        raise ApiError(400, "没有需要修改的字段")
    with transaction() as db:
        if f.get("required_count", original["required_count"]) < original["assigned_count"]:
            raise ApiError(409, f"需求人数不能少于已安排人数（{original['assigned_count']} 人）")
        # 改了时间：已安排的人不能因此与其他班次冲突
        start, end = f.get("start_time", original["start_time"]), f.get("end_time", original["end_time"])
        if (start, end) != (original["start_time"], original["end_time"]):
            people = rows(db.execute(
                "SELECT v.id, v.name FROM assignment a JOIN volunteer v ON v.id = a.volunteer_id "
                "WHERE a.shift_id = ? AND a.status IN ('ASSIGNED','COMPLETED')", (shift_id,)))
            for person in people:
                conflict = find_conflict(person["id"], start, end, shift_id)
                if conflict:
                    raise ApiError(409, f"调整后 {person['name']} 会与其他班次冲突（{describe_shift(conflict)}）")
        db.execute(f"UPDATE shift SET {', '.join(k + ' = ?' for k in f)} WHERE id = ?", (*f.values(), shift_id))
    return ok(_decorate(fetch_or_404(LIST_SQL + " WHERE s.id = ?", (shift_id,)), now_str()))


@bp.delete("/<int:shift_id>")
@admin_required
def delete_shift(shift_id):
    get_shift(shift_id)
    db = get_db()
    used = db.execute(
        "SELECT (SELECT COUNT(*) FROM assignment WHERE shift_id = ?) + (SELECT COUNT(*) FROM application WHERE shift_id = ?)",
        (shift_id, shift_id),
    ).fetchone()[0]
    if used:
        raise ApiError(409, "该班次已有排班或报名记录，不能删除")
    with transaction() as tx:
        tx.execute("DELETE FROM shift WHERE id = ?", (shift_id,))
    return ok(None)


@bp.get("/<int:shift_id>/status")
@admin_required
def shift_status(shift_id):
    return ok(fetch_or_404("SELECT * FROM v_shift_status WHERE shift_id = ?", (shift_id,), "班次不存在"))


@bp.get("/<int:shift_id>/roster")
@admin_required
def roster(shift_id):
    get_shift(shift_id)
    # core_queries.sql ⑦：只返回占用名额的调度，已取消的保留在库中但不显示
    return ok(rows(get_db().execute(
        """
        SELECT a.id AS assignment_id, v.id AS volunteer_id, v.name, v.student_no, v.phone, v.skill,
               a.status, a.assigned_at, a.check_in_at, a.check_out_at, au.username AS assigned_by_name
        FROM assignment a
        JOIN volunteer v ON v.id = a.volunteer_id
        JOIN admin_user au ON au.id = a.assigned_by
        WHERE a.shift_id = ? AND a.status IN ('ASSIGNED','COMPLETED')
        ORDER BY a.assigned_at, v.student_no
        """,
        (shift_id,),
    )))


@bp.get("/<int:shift_id>/applications")
@admin_required
def shift_applications(shift_id):
    get_shift(shift_id)
    return ok(rows(get_db().execute(
        """
        SELECT ap.id AS application_id, ap.status, ap.applied_at,
               v.id AS volunteer_id, v.name, v.student_no, v.skill, v.status AS volunteer_status
        FROM application ap JOIN volunteer v ON v.id = ap.volunteer_id
        WHERE ap.shift_id = ?
        ORDER BY CASE ap.status WHEN 'PENDING' THEN 0 WHEN 'APPROVED' THEN 1 ELSE 2 END, ap.applied_at
        """,
        (shift_id,),
    )))


@bp.get("/<int:shift_id>/candidates")
@admin_required
def candidates(shift_id):
    """候选人：所有未在本班次的志愿者，并标注 已报名 / 技能匹配 / 时间冲突 / 已停用。
    不过滤掉冲突和停用的人——管理员仍可点"安排"，由后端给出明确拒绝原因（演示四类规则）。"""
    shift = get_shift(shift_id)
    keyword = (request.args.get("keyword") or "").strip()
    sql = """
        SELECT v.id AS volunteer_id, v.name, v.student_no, v.skill, v.status,
               ap.status AS application_status,
               (SELECT COUNT(*) FROM assignment x WHERE x.volunteer_id = v.id AND x.status IN ('ASSIGNED','COMPLETED'))
                   AS assignment_count
        FROM volunteer v
        LEFT JOIN application ap ON ap.volunteer_id = v.id AND ap.shift_id = ?
        WHERE v.id NOT IN (SELECT volunteer_id FROM assignment WHERE shift_id = ? AND status IN ('ASSIGNED','COMPLETED'))
    """
    params = [shift_id, shift_id]
    if keyword:
        sql += " AND (v.name LIKE ? OR v.student_no LIKE ? OR v.skill LIKE ?)"
        params += [f"%{keyword}%"] * 3
    result = []
    for c in rows(get_db().execute(sql, params)):
        conflict = find_conflict(c["volunteer_id"], shift["start_time"], shift["end_time"], shift_id)
        c["conflict"] = describe_shift(conflict) if conflict else None
        c["skill_match"] = skill_match(c["skill"], shift["required_skill"])
        c["applied"] = c["application_status"] in ("PENDING", "APPROVED")
        c["available"] = c["status"] == "ACTIVE" and conflict is None
        result.append(c)
    result.sort(key=lambda c: (not c["available"], not c["applied"], not c["skill_match"],
                               c["assignment_count"], c["student_no"]))
    return ok({"shift": _decorate(shift, now_str()), "candidates": result})
