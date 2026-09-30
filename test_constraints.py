import sqlite3

conn = sqlite3.connect("sports_volunteer.db")
conn.execute("PRAGMA foreign_keys = ON")

def run_test(title, sql):
    print(f"\n--- 测试：{title} ---")
    try:
        conn.execute(sql)
        conn.commit()
        print("❌ 失败：数据库竟然允许插入了！")
    except sqlite3.IntegrityError as e:
        conn.rollback()
        print(f"✅ 成功拦截：{e}")
    except Exception as e:
        conn.rollback()
        print(f"⚠️ 其他错误：{e}")

# 1. 重复学号
run_test("重复学号", "INSERT INTO volunteer (student_no, name, status, password_hash) VALUES ('20260001', '测试', 'ACTIVE', 'x')")

# 2. 非法志愿者状态
run_test("非法志愿者状态", "INSERT INTO volunteer (student_no, name, status, password_hash) VALUES ('99999999', '测试', 'UNKNOWN', 'x')")

# 3. 班次人数为 0
run_test("班次需求人数为0", "INSERT INTO shift (event_id, role_id, start_time, end_time, required_count) VALUES (1, 1, '2026-09-28 10:00:00', '2026-09-28 12:00:00', 0)")

# 4. 班次开始晚于结束
run_test("班次开始晚于结束", "INSERT INTO shift (event_id, role_id, start_time, end_time, required_count) VALUES (1, 1, '2026-09-28 12:00:00', '2026-09-28 10:00:00', 2)")

# 5. 不存在的外键
run_test("不存在的赛事外键", "INSERT INTO shift (event_id, role_id, start_time, end_time, required_count) VALUES (999, 1, '2026-09-28 10:00:00', '2026-09-28 12:00:00', 2)")

# 6. 重复调度：志愿者1已在班次1
run_test("重复调度同一班次", "INSERT INTO assignment (volunteer_id, shift_id, assigned_by, status) VALUES (1, 1, 1, 'ASSIGNED')")

# 7. 重复报名：志愿者1已报名班次2
run_test("重复报名同一班次", "INSERT INTO application (volunteer_id, shift_id, status) VALUES (1, 2, 'PENDING')")

# 8. 非法 assignment 状态
run_test("非法调度状态", "INSERT INTO assignment (volunteer_id, shift_id, assigned_by, status) VALUES (10, 5, 1, 'PENDING')")

# 9. 非法 application 状态
run_test("非法报名状态", "INSERT INTO application (volunteer_id, shift_id, status) VALUES (10, 1, 'UNKNOWN')")

# 10. 签退早于签到
run_test("签退早于签到", "INSERT INTO assignment (volunteer_id, shift_id, assigned_by, status, check_in_at, check_out_at) VALUES (10, 5, 1, 'ASSIGNED', '2026-09-28 12:00:00', '2026-09-28 10:00:00')")

# 11. COMPLETED 状态但缺少签到或签退时间
run_test("COMPLETED 缺少时间", "INSERT INTO assignment (volunteer_id, shift_id, assigned_by, status) VALUES (10, 5, 1, 'COMPLETED')")

conn.close()