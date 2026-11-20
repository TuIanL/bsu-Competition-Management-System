-- ========================================================
-- 体育赛事志愿者调度数据库系统 (双端小程序协同版)
-- 文件名：schema.sql
-- 版本：V1.3 (在 V1.2 基础上：时间格式 CHECK、COMPLETED 不可回退触发器、视图补充关联字段)
-- 数据库：SQLite
-- V1.3 变更（均为"加固"，不改任何已有表名/字段名）：
--   1) event.event_date、shift.start_time/end_time 增加格式 CHECK，杜绝
--      '2026-10-28 9:00' 这类不规范时间导致字符串比较出错；
--   2) 新增触发器 trg_assignment_completed_final：COMPLETED 记录不允许再改状态；
--   3) 视图 v_shift_status 在末尾追加 event_id / role_id / note 三列（原列顺序不变）。
-- ========================================================

-- 1. 开启外键约束（必须）
PRAGMA foreign_keys = ON;

-- 2. 清理旧对象（按依赖倒序删除，方便一键重建）
DROP TRIGGER IF EXISTS trg_assignment_completed_final;
DROP VIEW IF EXISTS v_shift_status;
DROP TABLE IF EXISTS assignment;
DROP TABLE IF EXISTS application;
DROP TABLE IF EXISTS shift;
DROP TABLE IF EXISTS role;
DROP TABLE IF EXISTS event;
DROP TABLE IF EXISTS volunteer;
DROP TABLE IF EXISTS admin_user;

-- ========================================================
-- 3. 创建表结构 (严格按照依赖顺序)
-- ========================================================

-- 3.1 管理员表
CREATE TABLE admin_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 3.2 志愿者表 (新增 password_hash)
CREATE TABLE volunteer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_no TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    phone TEXT,
    skill TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','INACTIVE')),
    password_hash TEXT NOT NULL
);

-- 3.3 赛事表
CREATE TABLE event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    event_date TEXT NOT NULL
        CHECK (event_date IS date(event_date)),         -- V1.3：必须是合法的 YYYY-MM-DD（用 IS 防止 NULL 放行）
    venue TEXT,
    status TEXT NOT NULL DEFAULT 'PLANNED'
        CHECK (status IN ('PLANNED','ONGOING','FINISHED'))
);

-- 3.4 岗位表
CREATE TABLE role (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    required_skill TEXT,
    description TEXT
);

-- 3.5 班次表
CREATE TABLE shift (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    required_count INTEGER NOT NULL CHECK (required_count > 0),
    note TEXT,
    FOREIGN KEY (event_id) REFERENCES event(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (role_id) REFERENCES role(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    -- V1.3：必须是 YYYY-MM-DD HH:MM:SS，保证下面的字符串比较等价于时间比较
    CHECK (start_time IS datetime(start_time)),
    CHECK (end_time IS datetime(end_time)),
    CHECK (start_time < end_time)
);

-- 3.6 报名表 (新增)
CREATE TABLE application (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id INTEGER NOT NULL,
    shift_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','APPROVED','REJECTED','WITHDRAWN')),
    applied_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (volunteer_id, shift_id),
    FOREIGN KEY (volunteer_id) REFERENCES volunteer(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (shift_id) REFERENCES shift(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- 3.7 调度表 (新增签到签退字段与严格约束)
CREATE TABLE assignment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id INTEGER NOT NULL,
    shift_id INTEGER NOT NULL,
    assigned_by INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'ASSIGNED'
        CHECK (status IN ('ASSIGNED','COMPLETED','CANCELLED')),
    assigned_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    check_in_at TEXT,
    check_out_at TEXT,
    UNIQUE (shift_id, volunteer_id),
    FOREIGN KEY (volunteer_id) REFERENCES volunteer(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (shift_id) REFERENCES shift(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (assigned_by) REFERENCES admin_user(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    
    -- 【修复问题2】签退时间合法：有签退必须有签到，且签退不早于签到
    CHECK (check_out_at IS NULL OR (check_in_at IS NOT NULL AND check_out_at >= check_in_at)),
    
    -- 【修复问题3】完成状态必须同时有签到和签退时间
    CHECK (status != 'COMPLETED' OR (check_in_at IS NOT NULL AND check_out_at IS NOT NULL))
);

-- ========================================================
-- 4. 创建索引 (加速高频查询)
-- ========================================================
CREATE INDEX idx_shift_event ON shift(event_id);
CREATE INDEX idx_assignment_volunteer ON assignment(volunteer_id);
CREATE INDEX idx_assignment_shift ON assignment(shift_id);
CREATE INDEX idx_shift_time ON shift(start_time, end_time);
CREATE INDEX idx_application_volunteer ON application(volunteer_id);
CREATE INDEX idx_application_shift ON application(shift_id);

-- ========================================================
-- 5. 创建视图 v_shift_status (统计缺口)
-- ========================================================
CREATE VIEW v_shift_status AS
SELECT
    s.id AS shift_id,
    e.name AS event_name,
    r.name AS role_name,
    s.start_time,
    s.end_time,
    s.required_count,
    -- 统计有效排班：ASSIGNED(进行中) 和 COMPLETED(已完成) 都算占用名额，CANCELLED 不算
    COUNT(CASE WHEN a.status IN ('ASSIGNED','COMPLETED') THEN 1 END) AS assigned_count,
    s.required_count - COUNT(CASE WHEN a.status IN ('ASSIGNED','COMPLETED') THEN 1 END) AS remaining_count,
    -- V1.3 追加列（放在末尾，不影响按位置读取前 8 列的旧代码）
    s.event_id,
    s.role_id,
    s.note
FROM shift AS s
JOIN event AS e ON s.event_id = e.id
JOIN role AS r ON s.role_id = r.id
LEFT JOIN assignment AS a ON s.id = a.shift_id
GROUP BY s.id, e.name, r.name, s.start_time, s.end_time, s.required_count;

-- ========================================================
-- 6. 触发器（V1.3 新增）
-- 已完成（COMPLETED）的考勤记录不可再改为其他状态，防止误操作篡改考勤
-- （数据字典 assignment 状态流转说明中的规则，由数据库强制执行）
-- ========================================================
CREATE TRIGGER trg_assignment_completed_final
BEFORE UPDATE OF status ON assignment
WHEN OLD.status = 'COMPLETED' AND NEW.status <> 'COMPLETED'
BEGIN
    SELECT RAISE(ABORT, 'COMPLETED assignment cannot change status');
END;
