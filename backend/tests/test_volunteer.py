"""志愿者端测试：登录分流、我的班次、报名、签到签退、志愿时长、越权。"""
from datetime import datetime

from tests.conftest import data, message


def test_volunteer_login(anon):
    d = data(anon.login("20260001", "260001"))
    assert d["role"] == "volunteer" and d["name"] == "张礼宾" and d["must_change_password"] is True


def test_inactive_volunteer_cannot_login(anon):
    r = anon.login("20260010", "260010")
    assert r.status_code == 403 and "停用" in message(r)


def test_change_password(as_volunteer, anon):
    v = as_volunteer("20260002")
    assert message(v.post("/api/password", {"old_password": "x", "new_password": "abcdef"})) == "原密码不正确"
    assert v.post("/api/password", {"old_password": "260002", "new_password": "123"}).status_code == 400
    data(v.post("/api/password", {"old_password": "260002", "new_password": "abc12345"}))
    d = data(anon.login("20260002", "abc12345"))
    assert d["must_change_password"] is False


# ------------------------------------------------------------ 我的班次
def test_my_shifts(as_volunteer):
    shifts = {s["shift_id"]: s for s in data(as_volunteer("20260001").get("/api/volunteer/my-shifts"))}
    assert set(shifts) == {1, 3}
    assert shifts[1]["status"] == "COMPLETED" and shifts[1]["phase"] == "ended" and shifts[1]["minutes"] == 240
    assert shifts[3]["phase"] == "ongoing" and shifts[3]["can_checkout"] and not shifts[3]["can_checkin"]
    s2 = data(as_volunteer("20260002").get("/api/volunteer/my-shifts"))
    live = next(s for s in s2 if s["shift_id"] == 3)
    assert live["can_checkin"] and not live["can_checkout"]
    noshow = data(as_volunteer("20260011").get("/api/volunteer/my-shifts"))
    assert noshow[0]["no_show"] is True


def test_my_shifts_empty(as_volunteer):
    assert data(as_volunteer("20260020").get("/api/volunteer/my-shifts")) == []


# ------------------------------------------------------------ 签到签退 + 时长
def _assignment_id(volunteer_api, shift_id):
    return next(s["assignment_id"] for s in data(volunteer_api.get("/api/volunteer/my-shifts"))
                if s["shift_id"] == shift_id)


def test_checkin_checkout_flow_updates_hours(as_volunteer, clock):
    v = as_volunteer("20260002")
    aid = _assignment_id(v, 3)
    assert message(v.post(f"/api/assignments/{aid}/checkout")) == "请先签到"
    d = data(v.post(f"/api/assignments/{aid}/checkin"))
    assert d["check_in_at"] == "2026-11-19 10:20:00" and d["status"] == "ASSIGNED"
    assert message(v.post(f"/api/assignments/{aid}/checkin")) == "已经签到过了"
    clock.value = datetime(2026, 11, 19, 13, 30)  # 晚于班次结束 30 分钟签退
    d = data(v.post(f"/api/assignments/{aid}/checkout"))
    assert d["status"] == "COMPLETED"
    hours = data(v.get("/api/volunteer/my-hours"))
    # 有效时长只算班次内：10:20–13:00 = 160 分钟
    assert hours["total_minutes"] == 160 and hours["completed_count"] == 1
    assert hours["details"][0]["hours"] == 2.7
    assert v.post(f"/api/assignments/{aid}/checkout").status_code == 400


def test_checkin_window(as_volunteer, clock):
    v = as_volunteer("20260005")
    aid = _assignment_id(v, 5)  # 明天 09:00 开始
    assert "签到时间未到" in message(v.post(f"/api/assignments/{aid}/checkin"))
    clock.value = datetime(2026, 11, 20, 8, 30)  # 提前 30 分钟开放
    assert v.post(f"/api/assignments/{aid}/checkin").status_code == 200


def test_checkin_after_end_rejected(as_volunteer, clock):
    v = as_volunteer("20260016")
    aid = _assignment_id(v, 3)
    clock.value = datetime(2026, 11, 19, 13, 0)
    assert message(v.post(f"/api/assignments/{aid}/checkin")) == "班次已结束，不能签到"


def test_cannot_checkin_others_assignment(as_volunteer):
    owner = as_volunteer("20260002")
    aid = _assignment_id(owner, 3)
    intruder = as_volunteer("20260016")
    r = intruder.post(f"/api/assignments/{aid}/checkin")
    assert r.status_code == 403 and message(r) == "无权操作该数据"
    assert intruder.post(f"/api/assignments/{aid}/checkout").status_code == 403


def test_my_hours_clamped_to_shift(as_volunteer):
    d = data(as_volunteer("20260001").get("/api/volunteer/my-hours"))
    # 班次 09:00–13:00，签到 08:55 签退 13:02 → 有效 240 分钟
    assert d["total_minutes"] == 240 and d["total_hours"] == 4.0


# ------------------------------------------------------------ 可报名 + 报名
def test_positions_for_volunteer(as_volunteer):
    items = {p["shift_id"]: p for p in data(as_volunteer("20260001").get("/api/volunteer/positions"))}
    # 未开始、赛事未结束、未满员、本人未安排：5/6/7/8/10；班次9满员；3/4已开始
    assert set(items) == {5, 6, 7, 8, 10}
    assert items[5]["application_status"] == "PENDING" and items[5]["applied"]
    assert items[10]["application_status"] is None


def test_positions_hide_rejected_and_assigned(as_volunteer):
    v20 = {p["shift_id"] for p in data(as_volunteer("20260020").get("/api/volunteer/positions"))}
    assert 10 not in v20  # 被拒绝
    v5 = {p["shift_id"]: p for p in data(as_volunteer("20260005").get("/api/volunteer/positions"))}
    assert 5 not in v5 and v5[7]["conflict"] is True


def test_apply_flow(as_volunteer):
    v = as_volunteer("20260013")
    r = v.post("/api/applications", {"shift_id": 8})
    assert r.status_code == 201 and data(r)["status"] == "PENDING"
    r = v.post("/api/applications", {"shift_id": 8})
    assert r.status_code == 409 and message(r) == "该岗位已经报名"


def test_withdraw_and_reapply_reuses_row(as_volunteer):
    v = as_volunteer("20260002")
    item = next(p for p in data(v.get("/api/volunteer/positions")) if p["shift_id"] == 8)
    assert item["application_status"] == "WITHDRAWN"
    d = data(v.post("/api/applications", {"shift_id": 8}))
    assert d["id"] == item["application_id"]
    assert data(v.delete(f"/api/applications/{d['id']}"))["status"] == "WITHDRAWN"
    assert v.delete(f"/api/applications/{d['id']}").status_code == 409


def test_apply_rejections(as_volunteer):
    assert message(as_volunteer("20260020").post("/api/applications", {"shift_id": 10})) == "该报名已被拒绝，不能重新报名"
    assert message(as_volunteer("20260012").post("/api/applications", {"shift_id": 9})) == "该班次已满员"
    assert message(as_volunteer("20260012").post("/api/applications", {"shift_id": 3})) == "该班次已开始，不能报名"
    assert "时间冲突" in message(as_volunteer("20260005").post("/api/applications", {"shift_id": 7}))
    assert message(as_volunteer("20260005").post("/api/applications", {"shift_id": 5})) == "你已被安排到该班次"
    assert as_volunteer("20260012").post("/api/applications", {"shift_id": 999}).status_code == 404


def test_cannot_withdraw_others_application(as_volunteer):
    mine = data(as_volunteer("20260018").get("/api/volunteer/my-applications"))
    r = as_volunteer("20260012").delete(f"/api/applications/{mine[0]['application_id']}")
    assert r.status_code == 403


def test_full_chain(admin, as_volunteer, clock):
    """全链路：报名 → 管理员安排 → 我的班次出现 → 签到 → 签退 → 时长更新。"""
    v = as_volunteer("20260018")
    data(v.post("/api/applications", {"shift_id": 10}))
    data(admin.post("/api/assignments", {"volunteer_id": 18, "shift_id": 10}))
    mine = {s["shift_id"]: s for s in data(v.get("/api/volunteer/my-shifts"))}
    assert 10 in mine
    apps = {a["shift_id"]: a["status"] for a in data(v.get("/api/volunteer/my-applications"))}
    assert apps[10] == "APPROVED"
    clock.value = datetime(2026, 11, 22, 18, 0)
    data(v.post(f"/api/assignments/{mine[10]['assignment_id']}/checkin"))
    clock.value = datetime(2026, 11, 22, 21, 0)
    data(v.post(f"/api/assignments/{mine[10]['assignment_id']}/checkout"))
    assert data(v.get("/api/volunteer/my-hours"))["total_hours"] == 3.0
