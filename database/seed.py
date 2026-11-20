"""灌入演示数据（中网志愿者场景）。

V1.3 变更：
- 所有班次时间都相对"运行当天"生成，任何一天重跑都能演示：
  过去已完成的班次 / 今天正在进行可签到签退的班次 / 未来可报名的班次。
- 密码改为加盐 PBKDF2（与后端 werkzeug.check_password_hash 兼容），不再是无盐 sha256。
- 刻意设计了演示场景：满员班次、边界相接、时间冲突、停用志愿者、爽约记录、各状态报名。

用法：
    python database/seed.py                 # 默认写入 database/sports_volunteer.db
    python database/seed.py other.db
"""
import hashlib
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE / "sports_volunteer.db"

PBKDF2_ITERATIONS = 100_000
FMT = "%Y-%m-%d %H:%M:%S"


def hash_pw(password: str) -> str:
    """生成 werkzeug 兼容的 pbkdf2 哈希：pbkdf2:sha256:<轮数>$<盐>$<哈希>"""
    salt = secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${digest.hex()}"


VOLUNTEERS = [
    # 学号, 姓名, 电话, 技能, 状态
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

ROLES = [
    ("礼宾服务助理", "英语", "面向VIP嘉宾的高标准接待与服务"),          # 1
    ("包房服务助理", "服务意识", "负责包房区域的物资补充、观赛礼仪引导"),  # 2
    ("观众服务助理", "沟通", "园区内的移动百科全书，提供赛程答疑"),      # 3
    ("竞赛场地服务", "网球规则", "负责赛前场地筹备、赛中流程衔接、赛后整理"),  # 4
    ("球员服务", "英语", "在更衣室、健身房等区域解决球员需求"),          # 5
    ("媒体助理", "英语、写作", "协助新闻发布会、混合采访区等工作"),      # 6
    ("医疗协助", "急救", "协助医疗团队处理突发状况"),                  # 7
]


def seed(conn, now=None):
    """向已建好表结构的连接写入演示数据。now 可注入，便于测试。"""
    now = now or datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def day(offset, hh, mm=0):
        return (today + timedelta(days=offset, hours=hh, minutes=mm)).strftime(FMT)

    def date(offset):
        return (today + timedelta(days=offset)).strftime("%Y-%m-%d")

    # 今天"正在进行"的班次：从当前整点前 1 小时开始，持续 4 小时
    live_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    live_end = live_start + timedelta(hours=4)
    live = lambda dt, minutes=0: (dt + timedelta(minutes=minutes)).strftime(FMT)

    conn.execute("PRAGMA foreign_keys = ON")
    for table in ("application", "assignment", "shift", "role", "event", "volunteer", "admin_user"):
        conn.execute(f"DELETE FROM {table}")
    conn.execute("DELETE FROM sqlite_sequence")

    conn.executemany(
        "INSERT INTO admin_user (username, password_hash) VALUES (?, ?)",
        [("admin_zhongwang", hash_pw("admin123")), ("scheduler_li", hash_pw("sched123"))],
    )

    # 志愿者初始密码 = 学号后六位
    conn.executemany(
        "INSERT INTO volunteer (student_no, name, phone, skill, status, password_hash) VALUES (?, ?, ?, ?, ?, ?)",
        [(v[0], v[1], v[2], v[3], v[4], hash_pw(v[0][-6:])) for v in VOLUNTEERS],
    )

    conn.executemany(
        "INSERT INTO event (name, event_date, venue, status) VALUES (?, ?, ?, ?)",
        [
            ("2026中国网球公开赛 - WTA 1000", date(0), "国家网球中心-钻石球场", "ONGOING"),   # 1
            ("2026中国网球公开赛 - ATP 500", date(2), "国家网球中心-莲花球场", "PLANNED"),    # 2
            ("2026中国网球公开赛 - ITF青少年赛", date(-7), "国家网球中心-映月球场", "FINISHED"),  # 3
        ],
    )

    conn.executemany("INSERT INTO role (name, required_skill, description) VALUES (?, ?, ?)", ROLES)

    shifts = [
        # id: (event, role, start, end, required, note)
        (3, 3, day(-7, 9), day(-7, 13), 3, "映月球场 - 观众服务（已结束）"),            # 1 已满，含 1 条爽约
        (3, 7, day(-7, 13), day(-7, 17), 2, "映月球场 - 医疗站（已结束）"),             # 2
        (1, 1, live(live_start), live(live_end), 3, "钻石球场 - 礼宾服务（进行中）"),     # 3 可签到/签退
        (1, 4, live(live_start), live(live_end), 3, "钻石球场 - 竞赛场地（进行中）"),     # 4
        (1, 5, day(1, 9), day(1, 13), 3, "钻石球场 - 球员服务 上午"),                   # 5
        (1, 6, day(1, 13), day(1, 17), 3, "新闻发布厅 - 媒体助理 下午"),                # 6 与 5 边界相接
        (1, 3, day(1, 11), day(1, 15), 5, "钻石球场 - 观众服务 午间"),                  # 7 与 5 时间重叠
        (2, 2, day(2, 9), day(2, 17), 2, "莲花球场 - 包房服务"),                       # 8
        (2, 7, day(2, 9), day(2, 17), 2, "莲花球场 - 医疗协助"),                       # 9 已满员
        (2, 3, day(3, 18), day(3, 22), 4, "莲花球场 - 夜场观众服务"),                   # 10
    ]
    conn.executemany(
        "INSERT INTO shift (event_id, role_id, start_time, end_time, required_count, note) VALUES (?, ?, ?, ?, ?, ?)",
        shifts,
    )

    assigned_at = day(-10, 10)
    assignments = [
        # (volunteer, shift, admin, status, check_in, check_out)
        (1, 1, 1, "COMPLETED", day(-7, 8, 55), day(-7, 13, 2)),
        (3, 1, 1, "COMPLETED", day(-7, 9, 5), day(-7, 12, 50)),
        (11, 1, 1, "ASSIGNED", None, None),                         # 爽约：班次已结束仍未签到
        (7, 2, 1, "COMPLETED", day(-7, 12, 58), day(-7, 17, 0)),
        (14, 2, 1, "COMPLETED", day(-7, 13, 3), day(-7, 16, 55)),
        (1, 3, 1, "ASSIGNED", live(live_start, 5), None),             # 已签到，可演示签退
        (2, 3, 1, "ASSIGNED", None, None),                          # 未签到，可演示签到
        (16, 3, 2, "ASSIGNED", None, None),
        (4, 4, 2, "ASSIGNED", None, None),
        (19, 4, 2, "ASSIGNED", None, None),
        (5, 5, 1, "ASSIGNED", None, None),                          # 冲突/边界演示主角
        (6, 6, 1, "ASSIGNED", None, None),
        (8, 7, 2, "ASSIGNED", None, None),
        (7, 9, 1, "ASSIGNED", None, None),
        (14, 9, 1, "ASSIGNED", None, None),
    ]
    conn.executemany(
        "INSERT INTO assignment (volunteer_id, shift_id, assigned_by, status, assigned_at, check_in_at, check_out_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(v, s, a, st, assigned_at, ci, co) for v, s, a, st, ci, co in assignments],
    )

    applied_at = day(-12, 20)
    applications = [
        (1, 5, "PENDING"),
        (12, 5, "PENDING"),
        (13, 6, "PENDING"),
        (17, 7, "PENDING"),
        (8, 7, "APPROVED"),     # 已被采纳并排班
        (18, 8, "PENDING"),
        (2, 8, "WITHDRAWN"),    # 已撤回，可重新报名
        (20, 10, "REJECTED"),   # 已被拒绝，不可重新报名
    ]
    conn.executemany(
        "INSERT INTO application (volunteer_id, shift_id, status, applied_at) VALUES (?, ?, ?, ?)",
        [(v, s, st, applied_at) for v, s, st in applications],
    )
    conn.commit()


def main(db_path=DEFAULT_DB):
    conn = sqlite3.connect(str(db_path))
    try:
        seed(conn)
        print(f"演示数据插入成功：{db_path}")
        print("\n--- 班次状态视图 v_shift_status ---")
        for row in conn.execute(
            "SELECT shift_id, event_name, role_name, start_time, end_time, required_count, assigned_count, remaining_count "
            "FROM v_shift_status ORDER BY start_time"
        ):
            print(f"班次{row[0]:>2} | {row[3]} ~ {row[4][11:16]} | {row[2]:<6} | 需求 {row[5]} 已排 {row[6]} 缺口 {row[7]} | {row[1]}")
    finally:
        conn.close()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB)
