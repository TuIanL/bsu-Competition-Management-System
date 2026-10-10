# API 契约 v2（联调草案 · 双端）

> 文档归属：刘腾罡汇整 / 待章新怡确认｜版本：**API v2 联调草案**｜2026-10-02
> 配套事实源：database/schema.sql V1.2、docs/字段映射表.md、docs/01_项目范围说明.md
> 契约经后端与前端确认后再冻结；冻结后如需变更路径或字段，应先通过协作分支评审并同步更新字段映射。
> v2 变更：登录接口统一为 `/api/login` 并返回 `role`；新增志愿者端接口。

## 1. 通用约定

| 项 | 约定 |
|---|---|
| Base URL | `http://<host>:5000`（端点路径统一以 `/api` 开头）|
| 传输 | JSON（`Content-Type: application/json`） |
| 认证 | Flask `session`：管理员 `session['role']='admin'`；志愿者 `session['role']='volunteer'` 且 `session['volunteer_id']` |
| 鉴权失败 | 未登录 401；角色不匹配 / 越权 403 |
| 时间格式 | `YYYY-MM-DD HH:MM:SS`（北京时区 Asia/Shanghai） |
| 日期格式 | `YYYY-MM-DD` |
| 成功响应 | `{ "success": true, "data": <对象/数组> }` |
| 失败响应 | `{ "success": false, "message": "可理解中文" }` |
| SQL | **全部参数化**，禁止字符串拼接 |
| 请求封装 | 前端统一复用同一个 `utils/request.js`，志愿者端不另写一套 |

## 2. 统一错误码（message 面向用户，不暴露 traceback）

| 场景 | HTTP | message 示例 |
|---|---|---|
| 未登录 | 401 | 请先登录 |
| 账号或密码错误 | 401 | 账号或密码错误 |
| 越权（非本人数据/角色不符） | 403 | 无权操作该数据 |
| 字段校验失败 | 400 | 结束时间必须晚于开始时间 |
| 学号重复 | 409 | 学号 202301 已存在 |
| 重复调度 | 409 | 该志愿者已在本班次 |
| 时间冲突 | 409 | 该志愿者在该时段已有其他班次 |
| 班次已满 | 409 | 该班次已满员 |
| 志愿者已停用 | 409 | 该志愿者已停用，无法安排 |
| 重复报名 | 409 | 该岗位已经报名 |
| 未签到即签退 | 400 | 请先签到 |
| 资源不存在 | 404 | 记录不存在 |

## 3. 端点清单（管理端）

| # | 方法 | 路径 | 说明 | P0 |
|---|---|---|---|---|
| 1 | POST | `/api/login` | **统一登录**（管理员/志愿者共用，返回 role） | P0 |
| 2 | POST | `/api/logout` | 退出登录 | P0 |
| 3 | GET | `/api/volunteers` | 志愿者列表 | P0 |
| 4 | GET | `/api/volunteers/:id` | 志愿者详情 | P0 |
| 5 | POST | `/api/volunteers` | 新增志愿者（初始密码=学号后六位） | P0 |
| 6 | PUT | `/api/volunteers/:id` | 修改/停用志愿者 | P0 |
| 7 | GET / POST | `/api/events` | 赛事列表 / 新增 | P0 |
| 8 | GET / POST | `/api/roles` | 岗位列表 / 新增 | P0 |
| 9 | GET | `/api/shifts?event_id=` | 班次列表 | P0 |
| 10 | POST / PUT | `/api/shifts`，`/api/shifts/:id` | 新增 / 修改班次 | P0 |
| 11 | POST | `/api/assignments` | 创建调度（核心四规则） | P0 |
| 12 | DELETE | `/api/assignments/:id` | 取消调度（status=CANCELLED） | P0 |
| 13 | GET | `/api/shifts/:id/roster` | 班次名单 | P0 |
| 14 | GET | `/api/shifts/:id/status` | 班次缺口统计 | P0 |
| 15 | GET | `/api/shifts/:id/applications` | 查看该班次报名列表（调度参考） | P1 |
| 16 | GET | `/api/dashboard/stats` | Dashboard 统计（真实接口） | P0 |

## 4. 端点清单（志愿者端 · v2 新增）

| # | 方法 | 路径 | 说明 | P0 |
|---|---|---|---|---|
| 17 | GET | `/api/volunteer/positions` | 未来、赛事未结束、有名额且本人未报名/未排班的班次列表（`core_queries.sql` ④） | P0 |
| 18 | POST | `/api/applications` | 提交报名 `{shift_id}`（volunteer_id 取自 session） | P0 |
| 19 | GET | `/api/volunteer/my-shifts` | 当前志愿者已被分配的班次 | P0 |
| 20 | POST | `/api/assignments/:id/checkin` | 本人签到，写 check_in_at（status 仍 ASSIGNED） | P0 |
| 21 | POST | `/api/assignments/:id/checkout` | 本人签退，要求已签到，写 check_out_at 且 status=COMPLETED | P0 |
| 22 | GET | `/api/volunteer/my-hours` | 累计志愿时长（Σ check_out−check_in） | P0 |

## 5. 关键接口详述

### 5.1 POST /api/login（统一登录）
请求：`{ "username": "202301", "password": "******" }`
后端逻辑：先查 `admin_user`，命中→`role='admin'`；否则查 `volunteer`，命中→`role='volunteer'` 并写 `session['volunteer_id']`。
成功 200：
```json
{ "success": true, "data": { "role": "admin",     "id": 1, "name": "管理员" } }
{ "success": true, "data": { "role": "volunteer", "id": 5, "name": "张三" } }
```
前端根据 `role` 用 `wx.reLaunch` 跳转管理端/志愿者端首页（不用 tabBar）。

### 5.2 POST /api/assignments（创建调度 · 核心）
请求：`{ "volunteer_id": 1, "shift_id": 1 }`。`assigned_by` 从已登录管理员的 session 读取，不能信任前端传入值。
**校验顺序（业务层）：**
1. 志愿者存在且 `status='ACTIVE'` → 否则 `该志愿者已停用`
2. 不存在同一班次、同一志愿者的有效调度 → 否则 `该志愿者已在本班次`；若数据库中仅有 `CANCELLED` 记录，应复用该记录并重新检查规则后改回 `ASSIGNED`，因为 V1.2 的 UNIQUE 约束仍包含取消记录
3. 该志愿者其他 `ASSIGNED` 或 `COMPLETED` 班次与本班次时间不重叠（`start < 新end AND 新start < end`；边界相接允许）→ 否则 `时间冲突`，可参考 `core_queries.sql` ⑥
4. `v_shift_status.assigned_count < required_count` → 否则 `该班次已满员`

成功 201：`{ "success": true, "data": { "id":1, "status":"ASSIGNED", "assigned_at":"2026-10-02 10:00:00" } }`

### 5.3 POST /api/applications（志愿者报名）
请求：`{ "shift_id": 2 }`（volunteer_id 从 session 取）。后端还需确认志愿者为 `ACTIVE`，并按 `core_queries.sql` ④ 的口径校验班次尚未开始、所属赛事未结束、仍有名额且本人无有效排班（`ASSIGNED`/`COMPLETED`）；报名成功状态为 `PENDING`。
成功 201：`{ "success": true, "data": { "id":1, "shift_id":2, "status":"PENDING" } }`
失败 409：`{ "success": false, "message": "该岗位已经报名" }`（捕获 UNIQUE 约束冲突）
注意：UNIQUE(volunteer_id, shift_id) 下 `WITHDRAWN` 记录仍占用唯一键。报名接口三分支：
1. 无记录 → INSERT 新行（status=`PENDING`）
2. 已有 `WITHDRAWN` 记录 → UPDATE 原记录回 `PENDING` 并刷新 `applied_at`，**不新增行**（见 `data_dictionary.md` application 表说明）
3. 已有 `PENDING` / `APPROVED` 记录 → 返回 409 `该岗位已经报名`

### 5.4 POST /api/assignments/:id/checkin（签到）
校验：本人、`assignment.status='ASSIGNED'`、尚未签到，并且当前时间在班次开始和结束时间范围内；否则返回 403 或 400。
成功：写 `check_in_at=now`，`status` 保持 `ASSIGNED`。重复签到返回 400。

### 5.5 POST /api/assignments/:id/checkout（签退）
校验：本人、`assignment.status='ASSIGNED'`、已签到（`check_in_at` 非空），当前时间不早于班次结束时间和签到时间。成功：写 `check_out_at=now`，`status='COMPLETED'`。V1.2 数据库约束要求 `check_out_at >= check_in_at`。
未签到返回 400 `请先签到`。

### 5.6 GET /api/volunteer/my-hours（志愿时长）
```json
{ "success": true, "data": { "total_hours": 6.0,
  "details": [ { "event": "校运会篮球赛", "role": "检票员", "hours": 3.0 } ] } }
```
仅统计 `status='COMPLETED'` 的 assignment，时长 = `SUM(check_out_at − check_in_at)`。

### 5.7 GET /api/volunteer/positions（可报名班次 · `core_queries.sql` ④）
volunteer_id 从 session 取，SQL 中需作为参数传入**两次**（两个 `NOT IN` 子查询各一次）。口径：
1. `start_time > now`：班次尚未开始；
2. `e.status IN ('PLANNED','ONGOING')`：所属赛事未结束；
3. 不在该志愿者的 `PENDING`/`APPROVED` application 记录中（`WITHDRAWN` 不阻塞，撤回后该班次重新展示，走 5.3 的 UPDATE 重新报名）；
4. 不在该志愿者的有效排班（`ASSIGNED`/`COMPLETED`）记录中（`CANCELLED` 不阻塞，取消排班后该班次重新展示）；
5. `remaining = required_count - 有效排班数(ASSIGNED/COMPLETED) > 0`。

## 6. 待章新怡确认事项（对接点）

- [ ] 统一登录 `/api/login` 的查表顺序（先 admin 后 volunteer）是否可行？
- [ ] 响应格式统一为 `{success, data/message}`（沿用双端方案），是否替换掉 v1 的 `{data/error}`？
- [ ] 取消调度用 `DELETE /api/assignments/:id` 软取消（保留历史）是否 OK？
- [ ] 志愿者端页面的接口是否与 `docs/字段映射表.md` 字段一致？
- [ ] `/api/volunteer/positions` 按 5.7 实现：查询④需传 session volunteer_id 两次，列表排除 PENDING/APPROVED 报名及全部有效排班；WITHDRAWN 班次重新展示（V1.2.3 变更）
- [ ] 报名接口 `/api/applications` 实现三分支（无记录 INSERT / WITHDRAWN 更新原记录 / PENDING·APPROVED 返回 409），不能只写 INSERT
