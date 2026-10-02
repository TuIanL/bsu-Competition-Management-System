-- ========================================================
-- 体育赛事志愿者调度系统 · 核心查询 SQL
-- 文件名：core_queries.sql
-- 说明：后端 Flask API 参考查询，字段名与 database/schema.sql 一致
-- ========================================================

-- ① 查某班次的所有报名人（调度页用）
SELECT v.name, v.student_no, a.status
FROM application a
JOIN volunteer v ON a.volunteer_id = v.id
WHERE a.shift_id = ?
ORDER BY a.applied_at;

-- ② 查某志愿者的全部班次（我的班次页用）
SELECT s.start_time, s.end_time, e.name AS event_name, r.name AS role_name,
       a.status, a.check_in_at, a.check_out_at
FROM assignment a
JOIN shift s ON a.shift_id = s.id
JOIN event e ON s.event_id = e.id
JOIN role r ON s.role_id = r.id
WHERE a.volunteer_id = ?
ORDER BY s.start_time DESC;

-- ③ 查我的志愿时长（我的时长页用），返回分钟数
SELECT SUM(
  (julianday(check_out_at) - julianday(check_in_at)) * 24 * 60
) AS total_minutes
FROM assignment
WHERE volunteer_id = ?
  AND status = 'COMPLETED'
  AND check_in_at IS NOT NULL
  AND check_out_at IS NOT NULL;

-- ④ 查可报名的班次（志愿者端报名页用）
SELECT s.id, e.name AS event_name, r.name AS role_name,
       s.start_time, s.end_time, s.required_count,
       s.required_count - COUNT(a.id) AS remaining
FROM shift s
JOIN event e ON s.event_id = e.id
JOIN role r ON s.role_id = r.id
LEFT JOIN assignment a ON a.shift_id = s.id AND a.status IN ('ASSIGNED','COMPLETED')
WHERE s.start_time > datetime('now','localtime')
  AND e.status IN ('PLANNED','ONGOING')
GROUP BY s.id
HAVING remaining > 0;

-- ⑤ 查管理员 Dashboard 缺口排行
SELECT shift_id, event_name, role_name,
       required_count, assigned_count, remaining_count
FROM v_shift_status
ORDER BY remaining_count DESC
LIMIT 10;

-- ========================================================
-- 【补充】⑥ 时间冲突检测（R3，core_queries 原缺，建议后端采用）
-- 判断"志愿者 :vid 是否与班次 :sid 时间重叠"，返回行 = 冲突
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
-- ⑦ 查某班次已排班名单（管理端 roster 用）
-- 只返回占用名额的调度；已取消记录保留在数据库但不显示。
-- ========================================================
SELECT v.id AS volunteer_id, v.student_no, v.name, v.phone,
       a.status, a.assigned_at, a.check_in_at, a.check_out_at
FROM assignment AS a
JOIN volunteer AS v ON v.id = a.volunteer_id
WHERE a.shift_id = ?
  AND a.status IN ('ASSIGNED','COMPLETED')
ORDER BY a.assigned_at, v.student_no;
