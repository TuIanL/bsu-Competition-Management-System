# API 契约 v3（已实现 · 双端）

> 文档归属：赵梓嫣（接手前后端实现）｜版本：**API v3**｜2026-11-20
> 配套事实源：`database/schema.sql` V1.3、`backend/`（实现）、`backend/tests/`（47 项自动化测试即为本契约的可执行版本）
> v3 相对 v2 草案的变更见文末「变更记录」。路径、字段如需再改，先改本文件与测试，再改代码。

## 1. 通用约定

| 项 | 约定 |
|---|---|
| Base URL | `http://<host>:5000`，端点统一以 `/api` 开头（小程序端在 `miniprogram/config.js` 配置） |
| 传输 | JSON（`Content-Type: application/json`） |
| 认证 | 登录返回 `token`；之后每个请求带请求头 `Authorization: Bearer <token>`。token 由服务端密钥签名，内容为 `{role, id}`，有效期 7 天 |
| 鉴权失败 | 未登录 / token 无效或过期 → 401；角色不符 / 越权 / 账号已停用 → 403 |
| 时间格式 | 返回 `YYYY-MM-DD HH:MM:SS`；提交时可传 `YYYY-MM-DD HH:MM`，后端补齐秒（北京时间） |
| 日期格式 | `YYYY-MM-DD` |
| 成功响应 | `{ "success": true, "data": <对象/数组/null> }` |
| 失败响应 | `{ "success": false, "message": "可直接展示给用户的中文" }`，不暴露 traceback |
| SQL | 全部参数化（`?` 占位），无字符串拼接用户输入 |
| 前端封装 | `miniprogram/utils/request.js` 双端共用：成功 resolve(data)，失败 reject(Error(message))，401 自动回登录页 |

> **为什么从 Cookie Session 改为 token**：小程序的 `wx.request` 不会自动保存和携带 Cookie，用 Flask session 需要前端手动搬运 `Set-Cookie`，容易出错。token 方案的信息量与原 session 完全相同（role + id），由后端签名防伪造。

## 2. 错误码（message 面向用户）

| 场景 | HTTP | message |
|---|---|---|
| 未登录 / token 无效 | 401 | 请先登录 |
| 账号或密码错误 | 401 | 账号或密码错误 |
| 账号已停用（志愿者） | 403 | 账号已停用，请联系组委会 |
| 越权（非本人数据 / 角色不符） | 403 | 无权操作该数据 |
| 字段校验失败 | 400 | 结束时间必须晚于开始时间 / 学号不能为空 … |
| 学号重复 | 409 | 学号 20260001 已存在 |
| R1 志愿者已停用 | 409 | 该志愿者已停用，无法安排 |
| R2 重复调度 | 409 | 该志愿者已在本班次 |
| R3 时间冲突 | 409 | 该志愿者在该时段已有其他班次（球员服务，11月20日 09:00–13:00） |
| R4 班次已满 | 409 | 该班次已满员 |
| 班次已结束仍安排 | 409 | 该班次已结束，不能再安排 |
| 重复报名 | 409 | 该岗位已经报名 |
| 报名已被拒绝 | 409 | 该报名已被拒绝，不能重新报名 |
| 未签到即签退 | 400 | 请先签到 |
| 资源不存在 | 404 | 班次不存在 / 记录不存在 … |

## 3. 端点清单

### 3.1 通用（双端）

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/login` | 公开 | 统一登录，先查 admin_user 再查 volunteer（学号），返回 role |
| POST | `/api/logout` | 公开 | 无状态，前端清除 token 即退出 |
| GET | `/api/me` | 已登录 | 当前用户 |
| POST | `/api/password` | 已登录 | 修改本人密码 `{old_password, new_password}`（≥6 位） |
| GET | `/api/health` | 公开 | 健康检查 |

### 3.2 管理端（role=admin）

| 方法 | 路径 | 说明 | P |
|---|---|---|---|
| GET | `/api/dashboard/stats` | 统计卡片 + 缺员班次 Top10 | P0 |
| GET | `/api/volunteers?keyword=&status=` | 志愿者列表（含已排/已完成班次数） | P0 |
| GET | `/api/volunteers/:id` | 详情 | P0 |
| POST | `/api/volunteers` | 新增，初始密码 = 学号后六位 | P0 |
| PUT | `/api/volunteers/:id` | 修改 / 停用（`status`），返回 `future_assignment_count` 提醒 | P0 |
| POST | `/api/volunteers/:id/reset-password` | 重置为学号后六位 | 新增 |
| GET / POST | `/api/events` | 赛事列表（含班次数）/ 新增 | P0 |
| GET / PUT / DELETE | `/api/events/:id` | 详情 / 修改 / 删除（无班次时） | P0 |
| GET / POST | `/api/roles` | 岗位列表 / 新增（名称唯一） | P0 |
| GET / PUT / DELETE | `/api/roles/:id` | 详情 / 修改 / 删除（未被使用时） | P0 |
| GET | `/api/shifts?event_id=&scope=active\|ended\|all` | 班次列表（含 assigned/remaining、phase、待处理报名数） | P0 |
| POST | `/api/shifts` | 新增班次 | P0 |
| GET / PUT / DELETE | `/api/shifts/:id` | 详情 / 修改 / 删除（无排班和报名记录时） | P0 |
| GET | `/api/shifts/:id/roster` | 班次名单（排除 CANCELLED，含签到签退时间） | P0 |
| GET | `/api/shifts/:id/status` | 班次缺口（`v_shift_status` 一行） | P0 |
| GET | `/api/shifts/:id/applications` | 该班次报名列表（调度参考） | P1 ✅ |
| GET | `/api/shifts/:id/candidates?keyword=` | 候选志愿者 + 标注（已报名/技能匹配/冲突/停用） | P1 ✅ |
| POST | `/api/assignments` | 创建调度（核心四规则） | P0 |
| DELETE | `/api/assignments/:id` | 取消调度（软取消，status=CANCELLED） | P0 |
| POST | `/api/applications/:id/reject` | 拒绝报名（PENDING → REJECTED） | 新增 |

### 3.3 志愿者端（role=volunteer，数据一律限定为本人）

| 方法 | 路径 | 说明 | P |
|---|---|---|---|
| GET | `/api/volunteer/my-shifts` | 我的班次（含 `phase`、`can_checkin`、`can_checkout`、`no_show`、已完成时长） | P0 |
| GET | `/api/volunteer/positions` | 可报名班次（含本人报名状态、是否冲突、技能是否匹配） | P0 |
| GET | `/api/volunteer/my-applications` | 我的报名记录 | 新增 |
| POST | `/api/applications` | 提交报名 `{shift_id}` | P0 |
| DELETE | `/api/applications/:id` | 撤回本人报名（PENDING → WITHDRAWN） | 新增 |
| POST | `/api/assignments/:id/checkin` | 本人签到 | P0 |
| POST | `/api/assignments/:id/checkout` | 本人签退 → COMPLETED | P0 |
| GET | `/api/volunteer/my-hours` | 累计志愿时长 + 明细 | P0 |

## 4. 关键接口详述

### 4.1 POST /api/login
请求：`{ "username": "20260001", "password": "260001" }`
成功 200：
```json
{ "success": true, "data": {
  "token": "eyJ…", "role": "volunteer", "id": 1, "name": "张礼宾",
  "student_no": "20260001", "must_change_password": true } }
```
`must_change_password`：志愿者仍在使用初始密码（学号后六位）时为 true，前端提示修改。停用的志愿者返回 403。

### 4.2 POST /api/assignments（创建调度 · 核心）
请求：`{ "volunteer_id": 12, "shift_id": 8 }`。`assigned_by` 取自登录态，不信任前端。
在一个 `BEGIN IMMEDIATE` 写事务内按顺序校验（`backend/rules.py`）：

0. 班次未结束 → 否则「该班次已结束，不能再安排」
1. **R1** 志愿者 `ACTIVE`
2. **R2** 无同班次有效调度；若只有 `CANCELLED` 记录，则**复用原记录**改回 `ASSIGNED`（UNIQUE 包含取消记录）
3. **R3** 与本人其他 `ASSIGNED/COMPLETED` 班次不重叠：`新start < 旧end AND 旧start < 新end`，边界相接允许
4. **R4** 有效调度数 `< required_count`

成功后：若该志愿者报过名（PENDING），报名自动置为 `APPROVED`。
成功 201：`{ "id": 21, "status": "ASSIGNED", "assigned_at": "…", "volunteer_name": "陈物资", "assigned_count": 1, "remaining_count": 1 }`

### 4.3 DELETE /api/assignments/:id（取消调度）
仅 `ASSIGNED` 且**未签到**的记录可取消；改为 `CANCELLED`（保留历史）。对应报名若为 `APPROVED` 则退回 `PENDING`。

### 4.4 POST /api/applications（报名）
请求：`{ "shift_id": 8 }`（volunteer_id 取自登录态）。前置校验：班次未开始、赛事未结束、本人未被安排、未满员、与本人已安排班次不冲突。四分支：

| 已有记录 | 处理 |
|---|---|
| 无 | INSERT，status=PENDING |
| WITHDRAWN | UPDATE 原记录回 PENDING 并刷新 applied_at（不新增行） |
| PENDING / APPROVED | 409 该岗位已经报名 |
| REJECTED | 409 该报名已被拒绝，不能重新报名 |

### 4.5 签到 / 签退
- **签到** `POST /api/assignments/:id/checkin`：本人、`ASSIGNED`、未签到；当前时间在 **[班次开始前 30 分钟, 班次结束)** 内。写 `check_in_at`，status 仍为 `ASSIGNED`。
- **签退** `POST /api/assignments/:id/checkout`：本人、`ASSIGNED`、已签到（否则 400「请先签到」）。写 `check_out_at`，status=`COMPLETED`。允许提前签退（早退），时长相应减少。

### 4.6 GET /api/volunteer/my-hours（志愿时长）
```json
{ "success": true, "data": { "total_minutes": 240, "total_hours": 4.0, "completed_count": 1,
  "details": [ { "assignment_id": 1, "event": "…ITF青少年赛", "role": "观众服务助理",
                 "start_time": "…09:00:00", "end_time": "…13:00:00",
                 "check_in_at": "…08:55:00", "check_out_at": "…13:02:00", "minutes": 240, "hours": 4.0 } ] } }
```
**有效时长** = `min(签退, 班次结束) − max(签到, 班次开始)`，只计班次时间内的在岗时间，防止提前签到或很晚才签退造成时长虚高（SQL 见 `core_queries.sql` ③）。

### 4.7 GET /api/volunteer/positions（可报名班次）
口径（`core_queries.sql` ④）：班次未开始、赛事未结束、本人未被安排、报名不是 REJECTED，且「仍有名额」或「本人已报名待安排」。每项附带 `application_status`、`application_id`、`conflict`、`skill_match`，前端据此显示「报名 / 已报名，待安排 / 时间冲突」。

### 4.8 GET /api/dashboard/stats
返回 `volunteer_total, volunteer_active, event_total, event_active, shift_total, shift_active, assignment_active, pending_applications, total_gap, gap_shift_count, on_duty_expected, on_duty_checked_in, gap_shifts[]`。全部为实时聚合，无写死数字。

## 5. 变更记录（v2 草案 → v3 实现）

| 变更 | 原因 |
|---|---|
| Cookie Session → `Authorization: Bearer token` | 小程序不自动携带 Cookie |
| `/api/dashboard/stats` 增加缺口、在岗签到率等字段 | Dashboard 要回答"哪里缺人" |
| 新增 `reset-password`、`/api/password`、`/api/me` | 数据字典要求"首次登录提示修改密码"，需要修改与重置入口 |
| 新增撤回报名、拒绝报名、我的报名 | 让 application 的 4 个状态都有明确的产生途径（原开放问题 Q2） |
| positions 返回本人已报名的班次（带状态） | 刷新页面后按钮仍能显示"已报名，待安排" |
| 签到窗口放宽为开始前 30 分钟；签退不再要求晚于班次结束 | 符合现场习惯；配合"有效时长"口径不会虚增时长 |
| 志愿时长改为有效时长（裁剪到班次时间内） | 防止签到签退时间异常导致时长虚高 |
| 班次已结束不允许再安排；已签到不允许取消 | 保护考勤数据 |
| 新增赛事/岗位/班次的删除接口（仅无引用时） | 配合 FK `ON DELETE RESTRICT`，给出可读提示 |
