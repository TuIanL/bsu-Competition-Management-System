"""调度核心业务规则（管理端分配 + 志愿者报名共用），集中在一处便于答辩讲解与测试。

R1 状态：仅 ACTIVE 志愿者可被安排
R2 重复：同一志愿者同一班次不可有两条有效调度
R3 冲突：志愿者有效班次（ASSIGNED/COMPLETED）时间不得重叠；边界相接（A.end == B.start）允许
R4 满员：有效调度人数达到 required_count 后不可再安排
"""
from core import ApiError, get_db, now_str, one

SHIFT_DETAIL_SQL = """
SELECT s.id, s.event_id, s.role_id, s.start_time, s.end_time, s.required_count, s.note,
       e.name AS event_name, e.venue, e.status AS event_status, e.event_date,
       r.name AS role_name, r.required_skill,
       v.assigned_count, v.remaining_count
FROM shift s
JOIN event e ON e.id = s.event_id
JOIN role r ON r.id = s.role_id
JOIN v_shift_status v ON v.shift_id = s.id
"""


def get_shift(shift_id):
    shift = one(get_db().execute(SHIFT_DETAIL_SQL + " WHERE s.id = ?", (shift_id,)))
    if shift is None:
        raise ApiError(404, "班次不存在")
    return shift


def find_conflict(volunteer_id, start_time, end_time, exclude_shift_id=None):
    """R3：返回与 [start_time, end_time) 重叠的一条有效班次（core_queries.sql ⑥），无冲突返回 None。"""
    return one(
        get_db().execute(
            """
            SELECT s.id, s.start_time, s.end_time, e.name AS event_name, r.name AS role_name
            FROM assignment a
            JOIN shift s ON s.id = a.shift_id
            JOIN event e ON e.id = s.event_id
            JOIN role r ON r.id = s.role_id
            WHERE a.volunteer_id = ?
              AND a.status IN ('ASSIGNED','COMPLETED')
              AND s.id <> ?
              AND ? < s.end_time
              AND s.start_time < ?
            ORDER BY s.start_time
            LIMIT 1
            """,
            (volunteer_id, exclude_shift_id or -1, start_time, end_time),
        )
    )


def describe_shift(shift):
    """例：球员服务，11月20日 09:00–13:00"""
    start = shift["start_time"]
    return f"{shift['role_name']}，{int(start[5:7])}月{int(start[8:10])}日 {start[11:16]}–{shift['end_time'][11:16]}"


def skill_match(volunteer_skill, required_skill):
    """岗位技能为空视为匹配；否则岗位要求的任一关键词出现在志愿者技能里即匹配。"""
    if not required_skill:
        return True
    if not volunteer_skill:
        return False
    keywords = [k.strip() for k in required_skill.replace("，", "、").replace(",", "、").split("、") if k.strip()]
    return any(k in volunteer_skill for k in keywords)


def check_assignable(volunteer, shift):
    """按 R0→R4 顺序校验，返回已存在的调度记录（可能是 CANCELLED，用于复用）。"""
    db = get_db()
    if shift["end_time"] <= now_str():
        raise ApiError(409, "该班次已结束，不能再安排")
    if volunteer["status"] != "ACTIVE":
        raise ApiError(409, "该志愿者已停用，无法安排")  # R1
    existing = one(
        db.execute(
            "SELECT id, status FROM assignment WHERE volunteer_id = ? AND shift_id = ?",
            (volunteer["id"], shift["id"]),
        )
    )
    if existing and existing["status"] in ("ASSIGNED", "COMPLETED"):
        raise ApiError(409, "该志愿者已在本班次")  # R2
    conflict = find_conflict(volunteer["id"], shift["start_time"], shift["end_time"], shift["id"])
    if conflict:
        raise ApiError(409, f"该志愿者在该时段已有其他班次（{describe_shift(conflict)}）")  # R3
    count = db.execute(
        "SELECT COUNT(*) FROM assignment WHERE shift_id = ? AND status IN ('ASSIGNED','COMPLETED')",
        (shift["id"],),
    ).fetchone()[0]
    if count >= shift["required_count"]:
        raise ApiError(409, "该班次已满员")  # R4
    return existing
