"""报名：志愿者提交 / 撤回；管理员拒绝（通过 = 管理员在调度页安排该志愿者）。"""
from flask import Blueprint

from auth import admin_required, current_user, volunteer_required
from core import ApiError, body, now_str, ok, one, req_int, transaction
from rules import describe_shift, find_conflict, get_shift

bp = Blueprint("applications", __name__, url_prefix="/api/applications")


@bp.post("")
@volunteer_required
def submit():
    shift_id = req_int(body(), "shift_id", "班次")
    volunteer_id = current_user()["id"]  # 从登录态取，前端不传
    with transaction() as db:
        shift = get_shift(shift_id)
        if shift["start_time"] <= now_str():
            raise ApiError(409, "该班次已开始，不能报名")
        if shift["event_status"] == "FINISHED":
            raise ApiError(409, "该赛事已结束，不能报名")
        assigned = one(db.execute(
            "SELECT id FROM assignment WHERE volunteer_id = ? AND shift_id = ? AND status IN ('ASSIGNED','COMPLETED')",
            (volunteer_id, shift_id),
        ))
        if assigned:
            raise ApiError(409, "你已被安排到该班次")

        existing = one(db.execute(
            "SELECT id, status FROM application WHERE volunteer_id = ? AND shift_id = ?", (volunteer_id, shift_id)
        ))
        # 四分支（api-contract 5.3）
        if existing and existing["status"] in ("PENDING", "APPROVED"):
            raise ApiError(409, "该岗位已经报名")
        if existing and existing["status"] == "REJECTED":
            raise ApiError(409, "该报名已被拒绝，不能重新报名")
        if shift["remaining_count"] <= 0:
            raise ApiError(409, "该班次已满员")
        conflict = find_conflict(volunteer_id, shift["start_time"], shift["end_time"], shift_id)
        if conflict:
            raise ApiError(409, f"与你已安排的班次时间冲突（{describe_shift(conflict)}）")

        ts = now_str()
        if existing:  # WITHDRAWN → 复用原记录
            db.execute("UPDATE application SET status = 'PENDING', applied_at = ? WHERE id = ?", (ts, existing["id"]))
            app_id = existing["id"]
        else:
            app_id = db.execute(
                "INSERT INTO application (volunteer_id, shift_id, status, applied_at) VALUES (?, ?, 'PENDING', ?)",
                (volunteer_id, shift_id, ts),
            ).lastrowid
    return ok({"id": app_id, "shift_id": shift_id, "status": "PENDING", "applied_at": ts}, 201)


@bp.delete("/<int:application_id>")
@volunteer_required
def withdraw(application_id):
    with transaction() as db:
        app_row = one(db.execute("SELECT id, volunteer_id, status FROM application WHERE id = ?", (application_id,)))
        if app_row is None:
            raise ApiError(404, "报名记录不存在")
        if app_row["volunteer_id"] != current_user()["id"]:
            raise ApiError(403, "无权操作该数据")
        if app_row["status"] != "PENDING":
            raise ApiError(409, "只有待安排的报名可以撤回")
        db.execute("UPDATE application SET status = 'WITHDRAWN' WHERE id = ?", (application_id,))
    return ok({"id": application_id, "status": "WITHDRAWN"})


@bp.post("/<int:application_id>/reject")
@admin_required
def reject(application_id):
    with transaction() as db:
        app_row = one(db.execute("SELECT id, status FROM application WHERE id = ?", (application_id,)))
        if app_row is None:
            raise ApiError(404, "报名记录不存在")
        if app_row["status"] != "PENDING":
            raise ApiError(409, "只有待安排的报名可以拒绝")
        db.execute("UPDATE application SET status = 'REJECTED' WHERE id = ?", (application_id,))
    return ok({"id": application_id, "status": "REJECTED"})
