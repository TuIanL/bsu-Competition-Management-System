"""志愿者端：我的班次 / 可报名班次 / 我的报名 / 我的志愿时长（数据均限定为当前登录志愿者）。"""
from datetime import timedelta

from flask import Blueprint

from auth import current_user, volunteer_required
from core import DT_FMT, get_db, now, ok, rows, shift_phase
from routes.assignments import CHECKIN_EARLY_MINUTES
from rules import skill_match

bp = Blueprint("volunteer_me", __name__, url_prefix="/api/volunteer")

# 有效志愿时长（分钟）：只计班次时间范围内的在岗时间，避免提前签到或很晚才签退导致时长虚高
EFFECTIVE_MINUTES_SQL = """
CAST(ROUND(MAX(0, (julianday(MIN(a.check_out_at, s.end_time)) - julianday(MAX(a.check_in_at, s.start_time))) * 1440))
     AS INTEGER)
"""


@bp.get("/my-shifts")
@volunteer_required
def my_shifts():
    current = now()
    cur = current.strftime(DT_FMT)
    checkin_open = (current + timedelta(minutes=CHECKIN_EARLY_MINUTES)).strftime(DT_FMT)
    data = rows(get_db().execute(
        f"""
        SELECT a.id AS assignment_id, a.status, a.check_in_at, a.check_out_at,
               s.id AS shift_id, s.start_time, s.end_time, s.note,
               e.name AS event_name, e.venue, r.name AS role_name, r.description AS role_description,
               CASE WHEN a.status = 'COMPLETED' THEN {EFFECTIVE_MINUTES_SQL} END AS minutes
        FROM assignment a
        JOIN shift s ON s.id = a.shift_id
        JOIN event e ON e.id = s.event_id
        JOIN role r ON r.id = s.role_id
        WHERE a.volunteer_id = ? AND a.status IN ('ASSIGNED','COMPLETED')
        ORDER BY s.start_time
        """,
        (current_user()["id"],),
    ))
    for item in data:
        item["phase"] = shift_phase(item["start_time"], item["end_time"], cur)
        assigned = item["status"] == "ASSIGNED"
        # 开放签到：班次开始前 30 分钟 ≤ 当前 < 班次结束
        item["can_checkin"] = (assigned and not item["check_in_at"]
                               and item["start_time"] <= checkin_open and cur < item["end_time"])
        item["can_checkout"] = assigned and bool(item["check_in_at"])
        item["no_show"] = assigned and not item["check_in_at"] and item["phase"] == "ended"
    return ok(data)


@bp.get("/positions")
@volunteer_required
def positions():
    """可报名班次（core_queries.sql ④ 的口径），并附带本人的报名状态，便于按钮显示"已报名"。
    - 班次未开始、所属赛事未结束
    - 本人尚未被安排到该班次（ASSIGNED/COMPLETED）
    - 被拒绝（REJECTED）的不再展示
    - 有剩余名额；已满员但本人已报名待安排的仍展示（状态为"已报名"）
    """
    volunteer_id = current_user()["id"]
    db = get_db()
    skill = db.execute("SELECT skill FROM volunteer WHERE id = ?", (volunteer_id,)).fetchone()[0]
    cur = now().strftime(DT_FMT)
    data = rows(db.execute(
        """
        SELECT s.id AS shift_id, s.start_time, s.end_time, s.required_count, s.note,
               e.name AS event_name, e.venue, r.name AS role_name, r.required_skill, r.description AS role_description,
               v.remaining_count AS remaining, ap.id AS application_id, ap.status AS application_status,
               EXISTS (
                   SELECT 1 FROM assignment x JOIN shift xs ON xs.id = x.shift_id
                   WHERE x.volunteer_id = ? AND x.status IN ('ASSIGNED','COMPLETED')
                     AND s.start_time < xs.end_time AND xs.start_time < s.end_time
               ) AS conflict
        FROM shift s
        JOIN event e ON e.id = s.event_id
        JOIN role r ON r.id = s.role_id
        JOIN v_shift_status v ON v.shift_id = s.id
        LEFT JOIN application ap ON ap.shift_id = s.id AND ap.volunteer_id = ?
        WHERE s.start_time > ?
          AND e.status IN ('PLANNED','ONGOING')
          AND s.id NOT IN (SELECT shift_id FROM assignment WHERE volunteer_id = ? AND status IN ('ASSIGNED','COMPLETED'))
          AND (ap.status IS NULL OR ap.status <> 'REJECTED')
          AND (v.remaining_count > 0 OR ap.status IN ('PENDING','APPROVED'))
        ORDER BY s.start_time
        """,
        (volunteer_id, volunteer_id, cur, volunteer_id),
    ))
    for item in data:
        item["conflict"] = bool(item["conflict"])
        item["skill_match"] = skill_match(skill, item["required_skill"])
        item["applied"] = item["application_status"] in ("PENDING", "APPROVED")
    return ok(data)


@bp.get("/my-applications")
@volunteer_required
def my_applications():
    return ok(rows(get_db().execute(
        """
        SELECT ap.id AS application_id, ap.status, ap.applied_at,
               s.id AS shift_id, s.start_time, s.end_time, e.name AS event_name, r.name AS role_name
        FROM application ap
        JOIN shift s ON s.id = ap.shift_id
        JOIN event e ON e.id = s.event_id
        JOIN role r ON r.id = s.role_id
        WHERE ap.volunteer_id = ?
        ORDER BY ap.applied_at DESC
        """,
        (current_user()["id"],),
    )))


@bp.get("/my-hours")
@volunteer_required
def my_hours():
    details = rows(get_db().execute(
        f"""
        SELECT a.id AS assignment_id, e.name AS event, r.name AS role, s.start_time, s.end_time,
               a.check_in_at, a.check_out_at, {EFFECTIVE_MINUTES_SQL} AS minutes
        FROM assignment a
        JOIN shift s ON s.id = a.shift_id
        JOIN event e ON e.id = s.event_id
        JOIN role r ON r.id = s.role_id
        WHERE a.volunteer_id = ? AND a.status = 'COMPLETED'
        ORDER BY s.start_time DESC
        """,
        (current_user()["id"],),
    ))
    for d in details:
        d["hours"] = round(d["minutes"] / 60, 1)
    total_minutes = sum(d["minutes"] for d in details)
    return ok({
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 1),
        "completed_count": len(details),
        "details": details,
    })
