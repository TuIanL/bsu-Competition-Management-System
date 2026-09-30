# 体育赛事志愿者调度数据库——数据字典 (V1.2)

- 项目名称：体育赛事志愿者调度数据库系统（双端小程序协同版）
- 数据库类型：SQLite
- 文档版本：V1.2（在 V1.0 冻结版基础上，为支撑志愿者端新增字段与表；本版本定稿后同样不再变更结构）
- 相对 V1.0 的变更摘要：
  1. `volunteer` 表新增 `password_hash`，支撑志愿者自主登录
  2. 新增 `application`（报名）表，记录志愿者对具体班次的报名意向
  3. `assignment` 表新增 `check_in_at`、`check_out_at`，`status` 由两态扩展为三态（新增 `COMPLETED`，在**签退**时写入，而不是签到时）

---

## 1. admin_user（管理员表）

作用：记录后台管理员账号，用于登录和记录排班操作人。

| 字段名 | 含义 | 数据类型 | 约束 | 说明 |
|---|---|---|---|---|
| id | 管理员编号 | INTEGER | 主键、自增 | 唯一标识 |
| username | 用户名 | TEXT | 非空、唯一 | 登录用 |
| password_hash | 加密密码 | TEXT | 非空 | 不存明文 |
| created_at | 创建时间 | TEXT | 非空、默认当前时间 | 格式：`YYYY-MM-DD HH:MM:SS`；统一使用 `datetime('now','localtime')` 生成北京时间，所有设备和服务器时区应设为 `Asia/Shanghai` |

---

## 2. volunteer（志愿者表）

作用：记录所有志愿者的基本信息、状态与登录凭证。

| 字段名 | 含义 | 数据类型 | 约束 | 说明 |
|---|---|---|---|---|
| id | 志愿者编号 | INTEGER | 主键、自增 | 唯一标识 |
| student_no | 学号 | TEXT | 非空、唯一 | 用于唯一标识学生，也是志愿者端登录账号 |
| name | 姓名 | TEXT | 非空 |  |
| phone | 电话 | TEXT | 可空 | 联系方式 |
| skill | 技能 | TEXT | 可空 | 如：急救、检票 |
| status | 志愿者状态 | TEXT | 非空、默认 ACTIVE | 只能是 `ACTIVE` 或 `INACTIVE` |
| **password_hash** | **加密密码** | **TEXT** | **非空** | **【新增】志愿者端登录凭证，不存明文；初始密码建议统一设为学号后六位，首次登录强制提示修改，不做找回密码功能** |

> 变更说明：V1.0 中志愿者只是被管理的数据，不需要登录。双端方案要求志愿者本人登录查看班次、报名与签到，因此参照 `admin_user` 的做法补齐密码字段。

---

## 3. event（赛事表）

作用：记录体育赛事基本信息。

| 字段名 | 含义 | 数据类型 | 约束 | 说明 |
|---|---|---|---|---|
| id | 赛事编号 | INTEGER | 主键、自增 | 唯一标识 |
| name | 赛事名称 | TEXT | 非空 | 如：2026中国网球公开赛 |
| event_date | 比赛日期 | TEXT | 非空 | 格式：`YYYY-MM-DD` |
| venue | 比赛场馆 | TEXT | 可空 | 如：国家网球中心-钻石球场 |
| status | 赛事状态 | TEXT | 非空、默认 PLANNED | 只能是 `PLANNED`、`ONGOING`、`FINISHED` |

---

## 4. role（志愿岗位表）

作用：定义有哪些类型的志愿岗位。

| 字段名 | 含义 | 数据类型 | 约束 | 说明 |
|---|---|---|---|---|
| id | 岗位编号 | INTEGER | 主键、自增 | 唯一标识 |
| name | 岗位名称 | TEXT | 非空、唯一 | 如：礼宾服务助理、观众服务助理 |
| required_skill | 要求技能 | TEXT | 可空 | 如：英语、急救 |
| description | 岗位说明 | TEXT | 可空 | 岗位职责描述 |

---

## 5. shift（班次表）

作用：某场赛事中具体岗位的排班时间段和需要人数。

| 字段名 | 含义 | 数据类型 | 约束 | 说明 |
|---|---|---|---|---|
| id | 班次编号 | INTEGER | 主键、自增 | 唯一标识 |
| event_id | 所属赛事 | INTEGER | 非空、外键 | 关联 `event.id` |
| role_id | 所属岗位 | INTEGER | 非空、外键 | 关联 `role.id` |
| start_time | 开始时间 | TEXT | 非空 | 格式：`YYYY-MM-DD HH:MM:SS` |
| end_time | 结束时间 | TEXT | 非空 | 格式：`YYYY-MM-DD HH:MM:SS` |
| required_count | 需要人数 | INTEGER | 非空、大于 0 | 该班次需要几个志愿者 |
| note | 备注 | TEXT | 可空 | 补充说明 |

补充约束：`CHECK (start_time < end_time)`

---

## 6. application（报名表）【新增】

作用：记录志愿者对具体班次的报名意向，是志愿者端“我要报名”功能的落地表。志愿者报名的是**具体班次**而不是抽象岗位，因为班次才有明确的时间，后续签到、时长统计也依赖具体班次。

| 字段名 | 含义 | 数据类型 | 约束 | 说明 |
|---|---|---|---|---|
| id | 报名编号 | INTEGER | 主键、自增 | 唯一标识 |
| volunteer_id | 志愿者编号 | INTEGER | 非空、外键 | 关联 `volunteer.id` |
| shift_id | 班次编号 | INTEGER | 非空、外键 | 关联 `shift.id` |
| status | 报名状态 | TEXT | 非空、默认 PENDING | 只能是 `PENDING`、`APPROVED`、`REJECTED`、`WITHDRAWN` |
| applied_at | 报名时间 | TEXT | 非空、默认当前时间 | 格式：`YYYY-MM-DD HH:MM:SS`；统一使用 `datetime('now','localtime')` 生成北京时间 |

重点约束：`UNIQUE (volunteer_id, shift_id)`，防止同一志愿者对同一班次重复报名。

> 与 assignment 的关系：`application` 只是志愿者表达的报名意向，**不直接产生排班**。管理员在调度页面可以看到某班次的报名列表作为候选人参考，但真正把人排进班次、触发冲突/满员检测的动作，仍然是管理员在 `assignment` 表执行分配。这样设计是为了不改动原有的调度校验逻辑（冲突检测、满员检测只在 `assignment` 写入时触发一次），阶段一如时间不足，`application` 的审核环节可以先跳过，管理员直接参考报名列表手动分配。

> 重新报名说明：由于 `UNIQUE(volunteer_id, shift_id)` 约束，志愿者对同一班次只能有一条报名记录。若状态为 `WITHDRAWN` 后需重新报名，应更新原记录 `status` 回 `PENDING`，不重新插入新行。

---

## 7. assignment（调度表）

作用：记录志愿者被安排到哪个班次，是 volunteer 和 shift 的多对多中间表，同时记录签到结果。

| 字段名 | 含义 | 数据类型 | 约束 | 说明 |
|---|---|---|---|---|
| id | 调度编号 | INTEGER | 主键、自增 | 唯一标识 |
| volunteer_id | 志愿者编号 | INTEGER | 非空、外键 | 关联 `volunteer.id` |
| shift_id | 班次编号 | INTEGER | 非空、外键 | 关联 `shift.id` |
| assigned_by | 执行调度的管理员 | INTEGER | 非空、外键 | 关联 `admin_user.id` |
| status | 调度状态 | TEXT | 非空、默认 ASSIGNED | 只能是 `ASSIGNED`、`COMPLETED`、`CANCELLED` |
| assigned_at | 调度时间 | TEXT | 非空、默认当前时间 | 格式：`YYYY-MM-DD HH:MM:SS`；统一使用 `datetime('now','localtime')` 生成北京时间 |
| **check_in_at** | **签到时间** | **TEXT** | **可空** | **【V1.2 新增】志愿者本人签到时写入，格式同上；未签到为 NULL** |
| **check_out_at** | **签退时间** | **TEXT** | **可空** | **【V1.2 新增】志愿者本人签退时写入，要求 `check_in_at` 已存在才允许签退；志愿时长按 `check_out_at − check_in_at` 实际计算，比取班次计划时长更真实** |

重点约束：`UNIQUE (shift_id, volunteer_id)`，防止同一志愿者被重复安排到同一班次。

> 状态流转说明（V1.2 更新）：`ASSIGNED`（已分配，等待班次开始）→ 志愿者本人签到（写入 `check_in_at`，status **仍为 `ASSIGNED`**，表示“进行中”）→ 志愿者本人签退（写入 `check_out_at`，status 才变为 `COMPLETED`）；管理员也可将 `ASSIGNED` 直接改为 `CANCELLED`（取消安排）。**`COMPLETED` 之后不允许再改回其他状态**，如需撤销已完成记录，走人工线下处理，不在本阶段程序里开放该功能，避免误操作篡改考勤。

⚠️ 实施提醒：SQLite 不支持直接 `ALTER TABLE` 修改 `CHECK` 约束，`status` 三态、`check_in_at` 字段务必在建库脚本第一次执行时就写好，不要等程序开发到一半再回头改表结构。

---

## 8. 全局约束与关系说明

### 8.1 表关系

- `event` 1 : N `shift`（一场赛事有多个班次）
- `role` 1 : N `shift`（一个岗位可以有多个班次）
- `admin_user` 1 : N `assignment`（一个管理员可以执行多次调度）
- `volunteer` N : M `shift`（多对多关系，通过 `assignment` 表拆解）
- **`volunteer` 1 : N `application`（一个志愿者可以报名多个班次）【新增】**
- **`shift` 1 : N `application`（一个班次可以收到多份报名）【新增】**

### 8.2 关键约束

1. `volunteer.student_no` 必须唯一（UNIQUE）。
2. `role.name` 必须唯一（UNIQUE）。
3. `volunteer.status` 只能是 `ACTIVE` 或 `INACTIVE`（CHECK）。
4. `event.status` 只能是 `PLANNED`、`ONGOING` 或 `FINISHED`（CHECK）。
5. `assignment.status` 只能是 `ASSIGNED`、`COMPLETED` 或 `CANCELLED`（CHECK）。**【V1.2 更新：原为 ASSIGNED/CANCELLED 两态，新增 COMPLETED 表示已签退完成】**
6. `shift.required_count` 必须大于 0（CHECK）。
7. `shift.start_time` 必须早于 `shift.end_time`（CHECK）。
8. `assignment` 表中需有 `UNIQUE(shift_id, volunteer_id)`，防止同一志愿者被重复安排到同一班次。
9. 所有外键均需开启 `PRAGMA foreign_keys = ON` 才生效。
10. `event_date` 使用 `YYYY-MM-DD` 格式；`start_time`、`end_time`、`created_at`、`assigned_at`、**`check_in_at`**、**`check_out_at`**、**`applied_at`** 使用 `YYYY-MM-DD HH:MM:SS` 格式。
11. 项目统一使用 `datetime('now', 'localtime')` 生成本地时间。运行数据库的服务器或设备应配置为 `Asia/Shanghai` 时区，以确保生成北京时间。
12. 已取消的调度记录保留历史数据。重新安排同一志愿者时，更新原调度记录的 `status` 为 `ASSIGNED`，不重新插入重复记录；**若原记录已是 `COMPLETED`，不允许覆盖，需人工介入处理。【V1.2 补充】**
13. **`application` 表需有 `UNIQUE(volunteer_id, shift_id)`，防止同一志愿者对同一班次重复报名。【新增】**
14. **`application.status` 只能是 `PENDING`、`APPROVED`、`REJECTED` 或 `WITHDRAWN`（CHECK）。【新增】**
15. **`application` 中的报名意向不会自动写入 `assignment`；是否采纳报名、最终排班，仍由管理员在调度页手动执行。【新增，避免误解为自动分配】**
16. `assignment` 表中 `check_out_at` 必须晚于或等于 `check_in_at`，且 `check_out_at` 非空时 `check_in_at` 必须也非空：`CHECK (check_out_at IS NULL OR (check_in_at IS NOT NULL AND check_out_at >= check_in_at))`。
17. `assignment` 表中 `status` 为 `COMPLETED` 时，`check_in_at` 和 `check_out_at` 必须都非空：`CHECK (status != 'COMPLETED' OR (check_in_at IS NOT NULL AND check_out_at IS NOT NULL))`。