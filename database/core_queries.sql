-- ========================================================
-- 体育赛事志愿者调度系统 · 核心查询 SQL
-- 文件名：core_queries.sql
-- 说明：后端 Flask API 直接复制使用，字段名已验证
-- 版本：V1.3（与 backend/ 实现一致）
--   V1.2.3：WITHDRAWN 班次重新出现在可报名列表；报名接口四分支
--   V1.3 ：③ 志愿时长改为「有效时长」（裁剪到班次时间内）；
--          ④ 可报名列表同时返回本人已报名(PENDING/APPROVED)的班次及其状态，便于按钮显示「已报名」
-- ========================================================

-- ① 查某班次的所有报名人（调度页参考用）
SELECT v.name, v.student_no, a.status
FROM application a
JOIN volunteer v ON a.volunteer_id = v.id
WHERE a.shift_id = ?
ORDER BY a.applied_at;

-- ② 查某志愿者的全部班次（我的班次页用）
SELECT a.id AS assignment_id, s.start_time, s.end_time,
       e.name AS event_name, r.name AS role_name,
       a.status, a.check_in_at, a.check_out_at
FROM assignment a
JOIN shift s ON a.shift_id = s.id
JOIN event e ON s.event_id = e.id
JOIN role r ON s.role_id = r.id
WHERE a.volunteer_id = ?
ORDER BY s.start_time DESC;

-- ③ 查我的志愿时长（我的时长页用），返回分钟数
-- V1.3：只计班次时间范围内的在岗时间 = min(签退, 班次结束) − max(签到, 班次开始)
--       防止提前很久签到或很晚才签退导致时长虚高；SQLite 的 MIN/MAX 多参数形式是标量函数
SELECT SUM(MAX(0,
  (julianday(MIN(a.check_out_at, s.end_time)) - julianday(MAX(a.check_in_at, s.start_time))) * 24 * 60
)) AS total_minutes
FROM assignment a
JOIN shift s ON s.id = a.shift_id
WHERE a.volunteer_id = ?
  AND a.status = 'COMPLETED';

-- ④ 查该志愿者可报名的班次（志愿者端报名页用）
-- 参数：volunteer_id、当前时间、volunteer_id
-- 口径：未开始、赛事未结束、本人未被安排、报名不是 REJECTED，
--       且（仍有名额 或 本人已报名待安排——这样刷新后按钮仍显示「已报名」）
SELECT s.id AS shift_id, e.name AS event_name, r.name AS role_name,
       s.start_time, s.end_time, s.required_count,
       v.remaining_count AS remaining,
       ap.id AS application_id, ap.status AS application_status
FROM shift s
JOIN event e ON e.id = s.event_id
JOIN role r ON r.id = s.role_id
JOIN v_shift_status v ON v.shift_id = s.id
LEFT JOIN application ap ON ap.shift_id = s.id AND ap.volunteer_id = ?
WHERE s.start_time > ?
  AND e.status IN ('PLANNED','ONGOING')
  AND s.id NOT IN (SELECT shift_id FROM assignment WHERE volunteer_id = ? AND status IN ('ASSIGNED','COMPLETED'))
  AND (ap.status IS NULL OR ap.status <> 'REJECTED')
  AND (v.remaining_count > 0 OR ap.status IN ('PENDING','APPROVED'))
ORDER BY s.start_time;

-- ⑤ 查管理员 Dashboard 缺口排行
-- V1.3：只看未结束且仍有缺口的班次；参数：当前时间
SELECT shift_id, event_name, role_name,
       required_count, assigned_count, remaining_count
FROM v_shift_status
WHERE remaining_count > 0 AND end_time > ?
ORDER BY remaining_count DESC, start_time
LIMIT 10;

-- ========================================================
-- ⑥ 时间冲突检测（R3，排班/报名时调用）
-- 判断"志愿者 :vid 是否与新班次（起止时间 :start/:end）时间重叠"，
-- 返回行 = 存在冲突
-- ========================================================
SELECT 1
FROM assignment a
JOIN shift s ON a.shift_id = s.id
WHERE a.volunteer_id = ?
  AND a.status IN ('ASSIGNED','COMPLETED')
  AND ? < s.end_time        -- 新班次 start
  AND s.start_time < ?      -- 新班次 end
LIMIT 1;

-- ========================================================
-- ⑦ 查某班次已排班名单（管理端 roster / 班次名单用）
-- 只返回占用名额的调度；已取消记录保留在数据库但不显示。
-- ========================================================
SELECT a.id AS assignment_id, v.id AS volunteer_id, v.name, v.student_no,
       v.phone, a.status, a.assigned_at, a.check_in_at, a.check_out_at
FROM assignment AS a
JOIN volunteer AS v ON v.id = a.volunteer_id
WHERE a.shift_id = ?
  AND a.status IN ('ASSIGNED','COMPLETED')
ORDER BY a.assigned_at DESC, v.student_no;
