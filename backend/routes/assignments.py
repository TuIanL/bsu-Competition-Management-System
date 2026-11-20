"""调度：管理员分配 / 取消；志愿者本人签到 / 签退。"""
from datetime import timedelta

from flask import Blueprint

from auth import admin_required, current_user, volunteer_required
from core import ApiError, body, fetch_or_404, now, now_str, ok, one, parse_dt, req_int, transaction, DT_FMT
from rules import check_assignable, get_shift

bp = Blueprint("assignments", __name__, url_prefix="/api/assignments")

CHECKIN_EARLY_MINUTES = 30  # 允许提前 30 分钟签到

ASSIGNMENT_SQL = """
SELECT a.id, a.volunteer_id, a.shift_id, a.assigned_by, a.status, a.assigned_at, a.check_in_at, a.check_out_at,
       s.start_time, s.end_time
FROM assignment a JOIN shift s ON s.id = a.shift_id
WHERE a.id = ?
"""


@bp.post("")
@admin_required
def create_assignment():
    data = body()
    volunteer_id = req_int(data, "volunteer_id", "志愿者")
    shift_id = req_int(data, "shift_id", "班次")
    admin_id = current_user()["id"]  # assigned_by 取自登录态，不信任前端传值
    with transaction() as db:
        shift = get_shift(shift_id)
        volunteer = fetch_or_404("SELECT id, name, status FROM volunteer WHERE id = ?", (volunteer_id,), "志愿者不存在")
        existing = check_assignable(volunteer, shift)
        ts = now_str()
        if existing:  # 之前取消过：复用原记录（UNIQUE 约束包含已取消记录）
            db.execute(
                "UPDATE assignment SET status = 'ASSIGNED', assigned_by = ?, assigned_at = ?, "
                "check_in_at = NULL, check_out_at = NULL WHERE id = ?",
                (admin_id, ts, existing["id"]),
            )
            assignment_id = existing["id"]
        else:
            assignment_id = db.execute(
                "INSERT INTO assignment (volunteer_id, shift_id, assigned_by, status, assigned_at) "
                "VALUES (?, ?, ?, 'ASSIGNED', ?)",
                (volunteer_id, shift_id, admin_id, ts),
            ).lastrowid
        # 若该志愿者报过名，则把报名标记为已通过
        db.execute(
            "UPDATE application SET status = 'APPROVED' WHERE volunteer_id = ? AND shift_id = ? AND status = 'PENDING'",
            (volunteer_id, shift_id),
        )
        shift = get_shift(shift_id)
    return ok({
        "id": assignment_id,
        "status": "ASSIGNED",
        "assigned_at": ts,
        "volunteer_name": volunteer["name"],
        "assigned_count": shift["assigned_count"],
        "remaining_count": shift["remaining_count"],
    }, 201)


@bp.delete("/<int:assignment_id>")
@admin_required
def cancel_assignment(assignment_id):
    with transaction() as db:
        a = fetch_or_404(ASSIGNMENT_SQL, (assignment_id,), "调度记录不存在")
        if a["status"] == "CANCELLED":
            raise ApiError(409, "该安排已取消")
        if a["status"] == "COMPLETED":
            raise ApiError(409, "已完成的考勤记录不能取消")
        if a["check_in_at"]:
            raise ApiError(409, "该志愿者已签到，不能取消安排")
        db.execute("UPDATE assignment SET status = 'CANCELLED' WHERE id = ?", (assignment_id,))
        # 已通过的报名退回待审核，管理员可重新安排或拒绝
        db.execute(
            "UPDATE application SET status = 'PENDING' WHERE volunteer_id = ? AND shift_id = ? AND status = 'APPROVED'",
            (a["volunteer_id"], a["shift_id"]),
        )
        shift = get_shift(a["shift_id"])
    return ok({"id": assignment_id, "status": "CANCELLED",
               "assigned_count": shift["assigned_count"], "remaining_count": shift["remaining_count"]})


def _own_assignment(db, assignment_id):
    a = one(db.execute(ASSIGNMENT_SQL, (assignment_id,)))
    if a is None:
        raise ApiError(404, "记录不存在")
    if a["volunteer_id"] != current_user()["id"]:
        raise ApiError(403, "无权操作该数据")  # R6 越权保护
    if a["status"] != "ASSIGNED":
        raise ApiError(400, "该班次已签退或已取消")
    return a


@bp.post("/<int:assignment_id>/checkin")
@volunteer_required
def checkin(assignment_id):
    with transaction() as db:
        a = _own_assignment(db, assignment_id)
        if a["check_in_at"]:
            raise ApiError(400, "已经签到过了")
        current = now()
        opens = parse_dt(a["start_time"]) - timedelta(minutes=CHECKIN_EARLY_MINUTES)
        if current < opens:
            raise ApiError(400, f"签到时间未到（班次开始前 {CHECKIN_EARLY_MINUTES} 分钟开放）")
        if current >= parse_dt(a["end_time"]):
            raise ApiError(400, "班次已结束，不能签到")
        ts = current.strftime(DT_FMT)
        db.execute("UPDATE assignment SET check_in_at = ? WHERE id = ?", (ts, assignment_id))
    return ok({"id": assignment_id, "status": "ASSIGNED", "check_in_at": ts})


@bp.post("/<int:assignment_id>/checkout")
@volunteer_required
def checkout(assignment_id):
    with transaction() as db:
        a = _own_assignment(db, assignment_id)
        if not a["check_in_at"]:
            raise ApiError(400, "请先签到")  # R7
        ts = max(now_str(), a["check_in_at"])
        db.execute(
            "UPDATE assignment SET check_out_at = ?, status = 'COMPLETED' WHERE id = ?", (ts, assignment_id)
        )
    return ok({"id": assignment_id, "status": "COMPLETED", "check_in_at": a["check_in_at"], "check_out_at": ts})
