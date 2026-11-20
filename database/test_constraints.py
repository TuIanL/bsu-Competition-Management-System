"""数据库约束自检：每一项都"故意插入/修改非法数据"，期望被数据库拦截。

V1.3：在内存数据库中独立建库 + 灌种子数据后测试，不会污染 sports_volunteer.db；
任一项未被拦截时以非零状态码退出，便于自动化检查。

用法：python database/test_constraints.py
"""
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from seed import seed  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect(":memory:")
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript((HERE / "schema.sql").read_text(encoding="utf-8"))
seed(conn)

failures = 0


def run_test(title, sql):
    global failures
    print(f"\n--- 测试：{title} ---")
    try:
        conn.execute(sql)
        conn.commit()
        failures += 1
        print("❌ 失败：数据库竟然允许执行了！")
    except sqlite3.IntegrityError as e:
        conn.rollback()
        print(f"✅ 成功拦截：{e}")
    except Exception as e:  # noqa: BLE001
        conn.rollback()
        failures += 1
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
# 7. 重复报名：志愿者1已报名班次5
run_test("重复报名同一班次", "INSERT INTO application (volunteer_id, shift_id, status) VALUES (1, 5, 'PENDING')")
# 8. 非法 assignment 状态
run_test("非法调度状态", "INSERT INTO assignment (volunteer_id, shift_id, assigned_by, status) VALUES (10, 5, 1, 'PENDING')")
# 9. 非法 application 状态
run_test("非法报名状态", "INSERT INTO application (volunteer_id, shift_id, status) VALUES (10, 1, 'UNKNOWN')")
# 10. 签退早于签到
run_test("签退早于签到", "INSERT INTO assignment (volunteer_id, shift_id, assigned_by, status, check_in_at, check_out_at) VALUES (10, 5, 1, 'ASSIGNED', '2026-09-28 12:00:00', '2026-09-28 10:00:00')")
# 11. COMPLETED 状态但缺少签到或签退时间
run_test("COMPLETED 缺少时间", "INSERT INTO assignment (volunteer_id, shift_id, assigned_by, status) VALUES (10, 5, 1, 'COMPLETED')")
# 12. V1.3：时间格式不规范（缺秒）
run_test("班次时间格式不规范", "INSERT INTO shift (event_id, role_id, start_time, end_time, required_count) VALUES (1, 1, '2026-09-28 09:00', '2026-09-28 12:00:00', 2)")
# 13. V1.3：赛事日期格式不规范
run_test("赛事日期格式不规范", "INSERT INTO event (name, event_date) VALUES ('测试赛', '2026/9/28')")
# 14. V1.3：不存在的日期
run_test("不存在的日期", "INSERT INTO shift (event_id, role_id, start_time, end_time, required_count) VALUES (1, 1, '2026-02-30 09:00:00', '2026-02-30 12:00:00', 2)")
# 15. V1.3：COMPLETED 记录不可回退
run_test("已完成考勤被改回 ASSIGNED", "UPDATE assignment SET status = 'ASSIGNED' WHERE status = 'COMPLETED'")

conn.close()
print(f"\n共 15 项，未通过 {failures} 项")
sys.exit(1 if failures else 0)
