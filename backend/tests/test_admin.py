"""管理端测试：编号 T01–T14 对应《赵梓嫣个人执行方案》第五节核心测试矩阵。"""
from tests.conftest import data, message


# ------------------------------------------------------------ 登录与鉴权
def test_T01_admin_login_success(anon):
    d = data(anon.login("admin_zhongwang", "admin123"))
    assert d["role"] == "admin" and d["token"]


def test_T02_wrong_password(anon):
    r = anon.login("admin_zhongwang", "wrong")
    assert r.status_code == 401 and message(r) == "账号或密码错误"


def test_requires_login(anon):
    r = anon.get("/api/volunteers")
    assert r.status_code == 401 and message(r) == "请先登录"


def test_forged_token_rejected(anon):
    anon.token = "eyJyb2xlIjoiYWRtaW4iLCJpZCI6MX0.forged.signature"
    assert anon.get("/api/volunteers").status_code == 401


def test_volunteer_cannot_call_admin_api(as_volunteer):
    v = as_volunteer("20260001")
    r = v.get("/api/volunteers")
    assert r.status_code == 403 and message(r) == "无权操作该数据"
    assert v.post("/api/assignments", {"volunteer_id": 1, "shift_id": 8}).status_code == 403


# ------------------------------------------------------------ 志愿者 CRUD
def test_T03_create_volunteer_and_login_with_initial_password(admin, anon):
    r = admin.post("/api/volunteers", {"student_no": "20269999", "name": "新同学", "phone": "13900000000",
                                       "skill": "急救"})
    assert r.status_code == 201
    v = data(r)
    assert v["status"] == "ACTIVE" and "password_hash" not in v
    d = data(anon.login("20269999", "269999"))
    assert d["role"] == "volunteer" and d["must_change_password"] is True


def test_T04_duplicate_student_no(admin):
    r = admin.post("/api/volunteers", {"student_no": "20260001", "name": "重复"})
    assert r.status_code == 409 and message(r) == "学号 20260001 已存在"


def test_volunteer_validation(admin):
    assert message(admin.post("/api/volunteers", {"name": "无学号"})) == "学号不能为空"
    assert admin.post("/api/volunteers", {"student_no": "12", "name": "短"}).status_code == 400


def test_volunteer_search_and_deactivate(admin, anon):
    found = data(admin.get("/api/volunteers?keyword=急救"))
    assert {v["student_no"] for v in found} >= {"20260007", "20260014"}
    r = admin.put("/api/volunteers/14", {"status": "INACTIVE"})
    d = data(r)
    assert d["status"] == "INACTIVE" and d["future_assignment_count"] == 1
    assert anon.login("20260014", "260014").status_code == 403  # 停用后不能登录


def test_reset_password(admin, as_volunteer, anon):
    v = as_volunteer("20260003")
    data(v.post("/api/password", {"old_password": "260003", "new_password": "newpass1"}))
    assert anon.login("20260003", "260003").status_code == 401
    data(admin.post("/api/volunteers/3/reset-password"))
    assert anon.login("20260003", "260003").status_code == 200


# ------------------------------------------------------------ 赛事 / 岗位
def test_event_and_role_crud(admin):
    e = data(admin.post("/api/events", {"name": "校运会", "event_date": "2026-12-01", "venue": "田径场"}))
    assert e["status"] == "PLANNED"
    assert data(admin.put(f"/api/events/{e['id']}", {"status": "ONGOING"}))["status"] == "ONGOING"
    assert admin.post("/api/events", {"name": "x", "event_date": "2026/12/01"}).status_code == 400
    r = data(admin.post("/api/roles", {"name": "检票员", "required_skill": "检票"}))
    dup = admin.post("/api/roles", {"name": "检票员"})
    assert dup.status_code == 409 and "已存在" in message(dup)
    assert admin.delete(f"/api/roles/{r['id']}").status_code == 200
    assert admin.delete("/api/roles/1").status_code == 409  # 已被班次使用
    assert admin.delete(f"/api/events/{e['id']}").status_code == 200


# ------------------------------------------------------------ 班次
def test_T05_create_shift(admin):
    r = admin.post("/api/shifts", {"event_id": 2, "role_id": 3, "start_time": "2026-11-22 08:00",
                                   "end_time": "2026-11-22 12:00", "required_count": 3, "note": "早场"})
    s = data(r)
    assert r.status_code == 201 and s["start_time"] == "2026-11-22 08:00:00"
    assert s["assigned_count"] == 0 and s["remaining_count"] == 3 and s["phase"] == "upcoming"


def test_T06_invalid_shift_rejected(admin):
    base = {"event_id": 2, "role_id": 3, "required_count": 2}
    r = admin.post("/api/shifts", {**base, "start_time": "2026-11-22 12:00", "end_time": "2026-11-22 12:00"})
    assert r.status_code == 400 and message(r) == "结束时间必须晚于开始时间"
    r = admin.post("/api/shifts", {**base, "start_time": "2026-11-22 9:00", "end_time": "2026-11-22 12:00"})
    assert r.status_code == 400
    r = admin.post("/api/shifts", {**base, "start_time": "2026-11-22 08:00", "end_time": "2026-11-22 12:00",
                                   "required_count": 0})
    assert r.status_code == 400


def test_shift_update_rules(admin):
    # 班次4 已安排 2 人，需求不能改成 1
    r = admin.put("/api/shifts/4", {"required_count": 1})
    assert r.status_code == 409 and "不能少于已安排人数" in message(r)
    # 班次6（明天13–17，孙媒体）提前到 08–12 会与… 孙媒体没有别的班次 → 允许
    assert admin.put("/api/shifts/6", {"start_time": "2026-11-20 08:00", "end_time": "2026-11-20 12:00"}).status_code == 200
    # 班次5（钱球员 09–13）改到 11–15 不冲突；但先把钱球员排进班次6再改就冲突
    data(admin.post("/api/assignments", {"volunteer_id": 5, "shift_id": 10}))
    r = admin.put("/api/shifts/5", {"start_time": "2026-11-22 17:00", "end_time": "2026-11-22 19:00"})
    assert r.status_code == 409 and "钱球员" in message(r)


def test_delete_shift(admin):
    assert admin.delete("/api/shifts/1").status_code == 409
    s = data(admin.post("/api/shifts", {"event_id": 2, "role_id": 1, "start_time": "2026-11-23 08:00",
                                        "end_time": "2026-11-23 10:00", "required_count": 1}))
    assert admin.delete(f"/api/shifts/{s['id']}").status_code == 200


def test_shift_list_scope(admin):
    active = data(admin.get("/api/shifts?scope=active"))
    assert {s["id"] for s in active} == {3, 4, 5, 6, 7, 8, 9, 10}
    ended = data(admin.get("/api/shifts?scope=ended"))
    assert {s["id"] for s in ended} == {1, 2}
    assert data(admin.get("/api/shifts/9"))["is_full"] is True


# ------------------------------------------------------------ 调度四规则
def assign(admin, volunteer_id, shift_id):
    return admin.post("/api/assignments", {"volunteer_id": volunteer_id, "shift_id": shift_id})


def test_T07_assign_success(admin):
    r = assign(admin, 12, 8)
    d = data(r)
    assert r.status_code == 201 and d["assigned_count"] == 1 and d["remaining_count"] == 1
    roster = data(admin.get("/api/shifts/8/roster"))
    assert [p["student_no"] for p in roster] == ["20260012"]
    assert roster[0]["assigned_by_name"] == "admin_zhongwang"


def test_T08_duplicate_assignment(admin):
    r = assign(admin, 1, 3)
    assert r.status_code == 409 and message(r) == "该志愿者已在本班次"


def test_T09_time_conflict(admin):
    # 钱球员已在班次5（明天 09–13），班次7 为明天 11–15
    r = assign(admin, 5, 7)
    assert r.status_code == 409 and message(r).startswith("该志愿者在该时段已有其他班次")


def test_T10_boundary_is_not_conflict(admin):
    # 班次6 明天 13–17，与班次5 的 13:00 结束恰好相接
    assert assign(admin, 5, 6).status_code == 201


def test_T11_full_shift(admin):
    r = assign(admin, 12, 9)  # 班次9 需求 2，已有 2 人
    assert r.status_code == 409 and message(r) == "该班次已满员"


def test_T12_inactive_volunteer(admin):
    r = assign(admin, 10, 8)  # 王停用
    assert r.status_code == 409 and message(r) == "该志愿者已停用，无法安排"


def test_T13_cancel_and_reassign(admin):
    roster = data(admin.get("/api/shifts/9/roster"))
    target = next(p for p in roster if p["student_no"] == "20260014")
    d = data(admin.delete(f"/api/assignments/{target['assignment_id']}"))
    assert d["status"] == "CANCELLED" and d["remaining_count"] == 1
    assert len(data(admin.get("/api/shifts/9/roster"))) == 1
    assert admin.delete(f"/api/assignments/{target['assignment_id']}").status_code == 409
    # 重新安排：复用原记录（UNIQUE 包含已取消记录），id 不变
    again = data(assign(admin, 14, 9))
    assert again["id"] == target["assignment_id"]


def test_T14_dashboard_reflects_assignment(admin):
    before = data(admin.get("/api/dashboard/stats"))
    data(assign(admin, 12, 8))
    after = data(admin.get("/api/dashboard/stats"))
    assert after["assignment_active"] == before["assignment_active"] + 1
    assert after["total_gap"] == before["total_gap"] - 1
    gap8 = next(g for g in after["gap_shifts"] if g["shift_id"] == 8)
    assert gap8["remaining_count"] == 1


def test_dashboard_numbers(admin):
    d = data(admin.get("/api/dashboard/stats"))
    assert d["volunteer_total"] == 20 and d["volunteer_active"] == 18
    assert d["shift_active"] == 8 and d["pending_applications"] == 5
    assert d["on_duty_expected"] == 5 and d["on_duty_checked_in"] == 1
    assert all(g["remaining_count"] > 0 for g in d["gap_shifts"])


def test_cannot_assign_ended_shift(admin):
    r = assign(admin, 12, 1)
    assert r.status_code == 409 and "已结束" in message(r)


def test_cannot_cancel_after_checkin(admin):
    roster = data(admin.get("/api/shifts/3/roster"))
    checked = next(p for p in roster if p["check_in_at"])
    assert message(admin.delete(f"/api/assignments/{checked['assignment_id']}")) == "该志愿者已签到，不能取消安排"


# ------------------------------------------------------------ 报名参考 / 候选人
def test_assigning_applicant_approves_application(admin):
    apps = data(admin.get("/api/shifts/5/applications"))
    assert {a["student_no"]: a["status"] for a in apps} == {"20260001": "PENDING", "20260012": "PENDING"}
    data(assign(admin, 12, 5))
    apps = {a["student_no"]: a for a in data(admin.get("/api/shifts/5/applications"))}
    assert apps["20260012"]["status"] == "APPROVED"
    roster = data(admin.get("/api/shifts/5/roster"))
    aid = next(p["assignment_id"] for p in roster if p["student_no"] == "20260012")
    data(admin.delete(f"/api/assignments/{aid}"))
    apps = {a["student_no"]: a for a in data(admin.get("/api/shifts/5/applications"))}
    assert apps["20260012"]["status"] == "PENDING"  # 取消后退回待安排


def test_reject_application(admin):
    apps = data(admin.get("/api/shifts/6/applications"))
    aid = apps[0]["application_id"]
    assert data(admin.post(f"/api/applications/{aid}/reject"))["status"] == "REJECTED"
    assert admin.post(f"/api/applications/{aid}/reject").status_code == 409


def test_candidates_flags_and_order(admin):
    d = data(admin.get("/api/shifts/7/candidates"))
    cands = {c["student_no"]: c for c in d["candidates"]}
    assert "20260008" not in cands  # 已在本班次
    assert cands["20260005"]["conflict"] and not cands["20260005"]["available"]
    assert cands["20260010"]["status"] == "INACTIVE" and not cands["20260010"]["available"]
    assert cands["20260017"]["applied"] is True
    first = d["candidates"][0]
    assert first["student_no"] == "20260017"  # 可安排 + 已报名 排最前
    assert d["candidates"][-1]["available"] is False
