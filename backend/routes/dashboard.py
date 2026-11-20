"""管理端 Dashboard：统计卡片 + 缺员班次（数字全部来自实时聚合查询）。"""
from flask import Blueprint

from auth import admin_required
from core import get_db, now_str, ok, rows, shift_phase

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("/stats")
@admin_required
def stats():
    db = get_db()
    cur = now_str()
    today = cur[:10]
    counts = dict(db.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM volunteer)                                   AS volunteer_total,
          (SELECT COUNT(*) FROM volunteer WHERE status = 'ACTIVE')           AS volunteer_active,
          (SELECT COUNT(*) FROM event)                                       AS event_total,
          (SELECT COUNT(*) FROM event WHERE status <> 'FINISHED')            AS event_active,
          (SELECT COUNT(*) FROM shift)                                       AS shift_total,
          (SELECT COUNT(*) FROM shift WHERE end_time > :now)                 AS shift_active,
          (SELECT COUNT(*) FROM assignment WHERE status IN ('ASSIGNED','COMPLETED')) AS assignment_active,
          (SELECT COUNT(*) FROM application WHERE status = 'PENDING')        AS pending_applications,
          (SELECT COALESCE(SUM(remaining_count), 0) FROM v_shift_status
             WHERE remaining_count > 0 AND end_time > :now)                  AS total_gap,
          (SELECT COUNT(*) FROM v_shift_status
             WHERE remaining_count > 0 AND end_time > :now)                  AS gap_shift_count,
          (SELECT COUNT(*) FROM assignment a JOIN shift s ON s.id = a.shift_id
             WHERE a.status IN ('ASSIGNED','COMPLETED') AND s.start_time <= :now AND s.end_time > :now)
                                                                             AS on_duty_expected,
          (SELECT COUNT(*) FROM assignment a JOIN shift s ON s.id = a.shift_id
             WHERE a.status IN ('ASSIGNED','COMPLETED') AND a.check_in_at IS NOT NULL
               AND s.start_time <= :now AND s.end_time > :now)               AS on_duty_checked_in
        """,
        {"now": cur},
    ).fetchone())
    # 缺员班次：未结束且仍有缺口，按缺口从大到小（core_queries.sql ⑤）
    gaps = rows(db.execute(
        """
        SELECT shift_id, event_name, role_name, start_time, end_time,
               required_count, assigned_count, remaining_count
        FROM v_shift_status
        WHERE remaining_count > 0 AND end_time > ?
        ORDER BY remaining_count DESC, start_time
        LIMIT 10
        """,
        (cur,),
    ))
    for g_ in gaps:
        g_["phase"] = shift_phase(g_["start_time"], g_["end_time"], cur)
    counts["gap_shifts"] = gaps
    counts["today"] = today
    counts["generated_at"] = cur
    return ok(counts)
