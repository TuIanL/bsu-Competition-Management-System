"""管理端：赛事（event）与岗位（role）维护。"""
from flask import Blueprint

from auth import admin_required, login_required
from core import ApiError, body, fetch_or_404, get_db, ok, one, req_date, req_enum, req_str, rows, transaction

bp = Blueprint("catalog", __name__, url_prefix="/api")

EVENT_STATUSES = ("PLANNED", "ONGOING", "FINISHED")

EVENT_SQL = """
SELECT e.id, e.name, e.event_date, e.venue, e.status,
       (SELECT COUNT(*) FROM shift s WHERE s.event_id = e.id) AS shift_count
FROM event e
"""

ROLE_SQL = """
SELECT r.id, r.name, r.required_skill, r.description,
       (SELECT COUNT(*) FROM shift s WHERE s.role_id = r.id) AS shift_count
FROM role r
"""


# ------------------------------------------------------------------ 赛事
def _event_fields(data, partial):
    fields = {}
    if not partial or "name" in data:
        fields["name"] = req_str(data, "name", "赛事名称", max_len=60)
    if not partial or "event_date" in data:
        fields["event_date"] = req_date(data, "event_date", "比赛日期")
    if "venue" in data:
        fields["venue"] = req_str(data, "venue", "场馆", required=False, max_len=60)
    if "status" in data or not partial:
        fields["status"] = req_enum(data, "status", "赛事状态", EVENT_STATUSES, default="PLANNED")
    return fields


@bp.get("/events")
@login_required()
def list_events():
    return ok(rows(get_db().execute(EVENT_SQL + " ORDER BY e.event_date DESC, e.id DESC")))


@bp.get("/events/<int:event_id>")
@login_required()
def get_event(event_id):
    return ok(fetch_or_404(EVENT_SQL + " WHERE e.id = ?", (event_id,), "赛事不存在"))


@bp.post("/events")
@admin_required
def create_event():
    f = _event_fields(body(), partial=False)
    with transaction() as db:
        new_id = db.execute(
            "INSERT INTO event (name, event_date, venue, status) VALUES (?, ?, ?, ?)",
            (f["name"], f["event_date"], f.get("venue"), f["status"]),
        ).lastrowid
    return ok(fetch_or_404(EVENT_SQL + " WHERE e.id = ?", (new_id,)), 201)


@bp.put("/events/<int:event_id>")
@admin_required
def update_event(event_id):
    fetch_or_404("SELECT id FROM event WHERE id = ?", (event_id,), "赛事不存在")
    f = _event_fields(body(), partial=True)
    if not f:
        raise ApiError(400, "没有需要修改的字段")
    with transaction() as db:
        db.execute(f"UPDATE event SET {', '.join(k + ' = ?' for k in f)} WHERE id = ?", (*f.values(), event_id))
    return ok(fetch_or_404(EVENT_SQL + " WHERE e.id = ?", (event_id,)))


@bp.delete("/events/<int:event_id>")
@admin_required
def delete_event(event_id):
    event = fetch_or_404(EVENT_SQL + " WHERE e.id = ?", (event_id,), "赛事不存在")
    if event["shift_count"]:
        raise ApiError(409, "该赛事下已有班次，不能删除（可将状态改为已结束）")
    with transaction() as db:
        db.execute("DELETE FROM event WHERE id = ?", (event_id,))
    return ok(None)


# ------------------------------------------------------------------ 岗位
def _role_fields(data, partial):
    fields = {}
    if not partial or "name" in data:
        fields["name"] = req_str(data, "name", "岗位名称", max_len=30)
    if "required_skill" in data:
        fields["required_skill"] = req_str(data, "required_skill", "技能要求", required=False, max_len=60)
    if "description" in data:
        fields["description"] = req_str(data, "description", "岗位说明", required=False, max_len=200)
    return fields


def _ensure_role_name_unique(db, name, exclude_id=None):
    if one(db.execute("SELECT id FROM role WHERE name = ? AND id <> ?", (name, exclude_id or -1))):
        raise ApiError(409, f"岗位“{name}”已存在")


@bp.get("/roles")
@login_required()
def list_roles():
    return ok(rows(get_db().execute(ROLE_SQL + " ORDER BY r.id")))


@bp.get("/roles/<int:role_id>")
@login_required()
def get_role(role_id):
    return ok(fetch_or_404(ROLE_SQL + " WHERE r.id = ?", (role_id,), "岗位不存在"))


@bp.post("/roles")
@admin_required
def create_role():
    f = _role_fields(body(), partial=False)
    with transaction() as db:
        _ensure_role_name_unique(db, f["name"])
        new_id = db.execute(
            "INSERT INTO role (name, required_skill, description) VALUES (?, ?, ?)",
            (f["name"], f.get("required_skill"), f.get("description")),
        ).lastrowid
    return ok(fetch_or_404(ROLE_SQL + " WHERE r.id = ?", (new_id,)), 201)


@bp.put("/roles/<int:role_id>")
@admin_required
def update_role(role_id):
    fetch_or_404("SELECT id FROM role WHERE id = ?", (role_id,), "岗位不存在")
    f = _role_fields(body(), partial=True)
    if not f:
        raise ApiError(400, "没有需要修改的字段")
    with transaction() as db:
        if "name" in f:
            _ensure_role_name_unique(db, f["name"], role_id)
        db.execute(f"UPDATE role SET {', '.join(k + ' = ?' for k in f)} WHERE id = ?", (*f.values(), role_id))
    return ok(fetch_or_404(ROLE_SQL + " WHERE r.id = ?", (role_id,)))


@bp.delete("/roles/<int:role_id>")
@admin_required
def delete_role(role_id):
    role = fetch_or_404(ROLE_SQL + " WHERE r.id = ?", (role_id,), "岗位不存在")
    if role["shift_count"]:
        raise ApiError(409, "该岗位已被班次使用，不能删除")
    with transaction() as db:
        db.execute("DELETE FROM role WHERE id = ?", (role_id,))
    return ok(None)
