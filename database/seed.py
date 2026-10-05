import sqlite3
import hashlib

conn = sqlite3.connect("sports_volunteer.db")
conn.execute("PRAGMA foreign_keys = ON")

# 清空旧数据
conn.execute("DELETE FROM application")
conn.execute("DELETE FROM assignment")
conn.execute("DELETE FROM shift")
conn.execute("DELETE FROM role")
conn.execute("DELETE FROM event")
conn.execute("DELETE FROM volunteer")
conn.execute("DELETE FROM admin_user")
conn.execute("DELETE FROM sqlite_sequence")

def hash_pw(pw):
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

# 管理员
conn.executemany("""
INSERT INTO admin_user (username, password_hash) VALUES (?, ?)
""", [
    ("admin_zhongwang", hash_pw("admin123")),
    ("scheduler_li", hash_pw("sched123"))
])

# 志愿者（20人，密码统一用学号后六位）
volunteers = [
    ("20260001", "张礼宾", "13800000001", "英语流利、专业礼仪", "ACTIVE"),
    ("20260002", "李包房", "13800000002", "服务意识、沟通能力", "ACTIVE"),
    ("20260003", "王观众", "13800000003", "沟通能力、熟悉园区", "ACTIVE"),
    ("20260004", "赵竞赛", "13800000004", "细心、网球规则", "ACTIVE"),
    ("20260005", "钱球员", "13800000005", "英语流利、服务意识", "ACTIVE"),
    ("20260006", "孙媒体", "13800000006", "英语、写作能力", "ACTIVE"),
    ("20260007", "周医疗", "13800000007", "急救技能", "ACTIVE"),
    ("20260008", "吴特许", "13800000008", "沟通能力、服务意识", "ACTIVE"),
    ("20260009", "郑检票", "13800000009", "沟通、应急处理", "ACTIVE"),
    ("20260010", "王停用", "13800000010", "普通技能", "INACTIVE"),
    ("20260011", "冯引导", "13800000011", "沟通能力、英语", "ACTIVE"),
    ("20260012", "陈物资", "13800000012", "体力好、细心", "ACTIVE"),
    ("20260013", "褚翻译", "13800000013", "英语专八、口语流利", "ACTIVE"),
    ("20260014", "卫急救", "13800000014", "急救证、责任心强", "ACTIVE"),
    ("20260015", "蒋摄影", "13800000015", "摄影、视频剪辑", "INACTIVE"),
    ("20260016", "沈接待", "13800000016", "英语、形象气质佳", "ACTIVE"),
    ("20260017", "韩检票", "13800000017", "沟通、耐心", "ACTIVE"),
    ("20260018", "杨秩序", "13800000018", "责任心强、沟通", "ACTIVE"),
    ("20260019", "朱网球", "13800000019", "网球规则、英语", "ACTIVE"),
    ("20260020", "秦后勤", "13800000020", "吃苦耐劳、细心", "ACTIVE"),
]

conn.executemany("""
INSERT INTO volunteer (student_no, name, phone, skill, status, password_hash)
VALUES (?, ?, ?, ?, ?, ?)
""", [(v[0], v[1], v[2], v[3], v[4], hash_pw(v[0][-6:])) for v in volunteers])

# 赛事（日期改为 10 月，保证是未来日期）
conn.executemany("""
INSERT INTO event (name, event_date, venue, status) VALUES (?, ?, ?, ?)
""", [
    ("2026中国网球公开赛 - WTA 1000", "2026-10-28", "国家网球中心-钻石球场", "ONGOING"),
    ("2026中国网球公开赛 - ATP 500", "2026-10-29", "国家网球中心-莲花球场", "ONGOING"),
    ("2026中国网球公开赛 - ITF青少年赛", "2026-10-25", "国家网球中心-映月球场", "FINISHED")
])

# 岗位
conn.executemany("""
INSERT INTO role (name, required_skill, description) VALUES (?, ?, ?)
""", [
    ("礼宾服务助理", "英语", "面向VIP嘉宾的高标准接待与服务"),
    ("包房服务助理", "服务意识", "负责包房区域的物资补充、观赛礼仪引导"),
    ("观众服务助理", "沟通", "园区内的移动百科全书，提供赛程答疑"),
    ("竞赛场地服务", "网球规则", "负责赛前场地筹备、赛中流程衔接、赛后整理"),
    ("球员服务", "英语", "在更衣室、健身房等区域解决球员需求"),
    ("媒体助理", "英语、写作", "协助新闻发布会、混合采访区等工作"),
    ("医疗协助", "急救", "协助医疗团队处理突发状况")
])

# 班次（日期改为 10 月，未来日期，可被报名查询查到）
conn.executemany("""
INSERT INTO shift (event_id, role_id, start_time, end_time, required_count, note)
VALUES (?, ?, ?, ?, ?, ?)
""", [
    (1, 1, "2026-10-28 11:00:00", "2026-10-28 19:00:00", 3, "钻石球场 - 日场礼宾服务"),
    (1, 4, "2026-10-28 11:00:00", "2026-10-28 19:00:00", 4, "钻石球场 - 日场竞赛场地"),
    (1, 5, "2026-10-28 19:00:00", "2026-10-28 23:00:00", 3, "钻石球场 - 晚场球员服务"),
    (2, 3, "2026-10-29 11:00:00", "2026-10-29 19:00:00", 5, "莲花球场 - 日场观众服务"),
    (2, 2, "2026-10-29 11:00:00", "2026-10-29 19:00:00", 2, "莲花球场 - 日场包房服务"),
    (1, 6, "2026-10-30 13:00:00", "2026-10-30 21:00:00", 3, "新闻发布厅 - 媒体助理"),
    (1, 7, "2026-10-30 13:00:00", "2026-10-30 21:00:00", 2, "医疗站 - 急救协助")
])

# 报名意向
conn.executemany("""
INSERT INTO application (volunteer_id, shift_id, status) VALUES (?, ?, ?)
""", [
    (1, 2, "PENDING"), (2, 3, "PENDING"), (3, 4, "PENDING"),
    (4, 5, "PENDING"), (5, 6, "PENDING"), (6, 7, "PENDING"),
    (7, 1, "APPROVED")
])

# 排班（COMPLETED 记录时间同步改为 10 月）
conn.executemany("""
INSERT INTO assignment
(volunteer_id, shift_id, assigned_by, status, check_in_at, check_out_at)
VALUES (?, ?, ?, ?, ?, ?)
""", [
    (1, 1, 1, "ASSIGNED", None, None),
    (2, 1, 1, "ASSIGNED", None, None),
    (3, 1, 1, "ASSIGNED", None, None),

    (4, 2, 1, "ASSIGNED", None, None),
    (9, 2, 1, "ASSIGNED", None, None),
    (6, 2, 1, "COMPLETED", "2026-10-28 11:05:00", "2026-10-28 18:50:00"),

    (5, 3, 1, "ASSIGNED", None, None),

    (6, 4, 2, "ASSIGNED", None, None),
    (7, 4, 2, "ASSIGNED", None, None),
    (8, 4, 2, "ASSIGNED", None, None),

    (2, 6, 2, "ASSIGNED", None, None),

    (7, 7, 1, "COMPLETED", "2026-10-30 13:00:00", "2026-10-30 20:55:00"),
    (8, 7, 1, "COMPLETED", "2026-10-30 13:02:00", "2026-10-30 21:00:00")
])

conn.commit()
print("✅ 中网演示数据插入成功（日期已更新为10月）！")

print("\n--- 班次状态视图 v_shift_status ---")
rows = conn.execute("SELECT * FROM v_shift_status").fetchall()
for row in rows:
    print(f"班次ID:{row[0]} | 赛事:{row[1]} | 岗位:{row[2]} | 时间:{row[3]}~{row[4]} | 需求:{row[5]} | 已排:{row[6]} | 缺口:{row[7]}")

conn.close()