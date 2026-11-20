# 联调排查手册（技术支持用）

## 一、字段名对照表

| 表名 | 字段名 |
|---|---|
| admin_user | id, username, password_hash, created_at |
| volunteer | id, student_no, name, phone, skill, status, password_hash |
| event | id, name, event_date, venue, status |
| role | id, name, required_skill, description |
| shift | id, event_id, role_id, start_time, end_time, required_count, note |
| application | id, volunteer_id, shift_id, status, applied_at |
| assignment | id, volunteer_id, shift_id, assigned_by, status, assigned_at, check_in_at, check_out_at |

### 状态值必须用英文

- volunteer.status：ACTIVE / INACTIVE
- event.status：PLANNED / ONGOING / FINISHED
- application.status：PENDING / APPROVED / REJECTED / WITHDRAWN
- assignment.status：ASSIGNED / COMPLETED / CANCELLED

### 时间格式
YYYY-MM-DD HH:MM:SS

---

## 二、报错对照表

### 数据库正常拦截（不是 bug，是约束生效了）

| 报错信息 | 怎么处理 |
|---|---|
| UNIQUE constraint failed: application.volunteer_id, application.shift_id | 正常！志愿者重复报名。代码里捕获异常，返回“该岗位已经报名” |
| UNIQUE constraint failed: assignment.shift_id, assignment.volunteer_id | 正常！志愿者已被排到该班次。捕获异常返回提示 |
| FOREIGN KEY constraint failed | 正常！插入的 event_id/shift_id/volunteer_id 不存在。检查传进来的 ID |
| CHECK constraint failed: status IN (...) | 正常！status 值不合法。只能传英文枚举值 |
| CHECK constraint failed: start_time < end_time | 正常！班次开始时间比结束时间晚。检查前端传的时间 |
| CHECK constraint failed: required_count > 0 | 正常！班次需求人数传了 0 或负数。检查前端提交的 required_count 是否合法 |
| CHECK constraint failed: check_out_at IS NULL OR (check_in_at IS NOT NULL AND check_out_at >= check_in_at) | 正常！签退时缺签到时间，或签退时间早于签到时间。检查代码是否漏了签到就直接写签退 |
| CHECK constraint failed: status != 'COMPLETED' OR (check_in_at IS NOT NULL AND check_out_at IS NOT NULL) | 正常！标为 COMPLETED 但缺签到或签退时间。检查是否漏了签到 |

### 代码写错了（需要改代码）

| 报错信息 | 怎么处理 |
|---|---|
| no such column: xxx | 字段名错了。对照数据字典改成正确的 |
| no such table: xxx | 表名错了。数据库只有 7 张业务表 |
| database is locked | 多个程序同时写数据库。检查是否开了多个终端 |

---

## 三、一键恢复数据库

数据改乱了？在**项目根目录**运行任一方式：

```bash
# 方式一：通过后端重置并启动（推荐）
python backend/app.py --reset-db

# 方式二：只重建数据库（V1.3 起脚本可在任意目录运行）
python database/init_db.py
python database/seed.py
```

> V1.3 起种子数据按"运行当天"生成：今天有进行中的班次可签到，明天/后天有可报名班次，一周前有已完成记录。
> 不同日期重置后，班次的具体日期会变，但演示场景（冲突、边界、满员、停用、爽约）不变。

## 四、V1.3 新增约束的报错

| 报错信息 | 含义 |
|---|---|
| CHECK constraint failed: start_time IS datetime(start_time) | 班次时间格式不规范（如缺秒、`9:00` 未补零、日期不存在） |
| CHECK constraint failed: event_date IS date(event_date) | 赛事日期不是合法的 YYYY-MM-DD |
| COMPLETED assignment cannot change status | 触发器拦截：已完成考勤不能改回其他状态 |
