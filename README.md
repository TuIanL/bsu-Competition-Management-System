# bsu-Competition-Management-System

> 体育赛事志愿者调度系统 · 双端小程序
> 课程项目 · 技术栈：**微信小程序前端 + Flask JSON API + SQLite**
> 项目管理员 / 系统分析员：刘腾罡｜后端：章新怡｜前端+测试：赵梓嫣｜系统设计/DBA：张照锐

## 1. 项目简介

单个小程序双端：**管理端**由组委会维护志愿者、赛事、岗位与班次并执行调度；**志愿者端**由志愿者
自助查看班次、报名岗位、签到签退、查看实际志愿时长。系统通过**数据库约束（UNIQUE/CHECK/FK）+
后端业务层校验** 阻止重复调度、时间冲突、超员与重复报名，并展示班次名单与缺口统计。

> 定位：报名意向由志愿者提交，**最终排班动作仍由管理员确认执行**。

## 2. 目录结构

```
.
├── README.md
├── database/                    # 数据库（张照锐）
│   ├── schema.sql               # Schema V1.2 冻结版（7 表 + 视图 v_shift_status）
│   ├── init_db.py               # 一键建库（执行 schema.sql）
│   ├── seed.py                  # 演示数据（20 志愿者/3 赛事/7 岗位/7 班次/报名/排班）
│   ├── test_constraints.py      # 11 项约束测试
│   ├── core_queries.sql         # 7 条参考查询（含名单、冲突检测）
│   ├── data_dictionary.md       # Schema V1.2 数据字典
│   ├── troubleshooting.md       # 数据库字段与常见报错排查
│   └── ER图.svg                 # 数据库 ER 图
├── docs/                        # 文档（刘腾罡）
│   ├── 00_项目总控台.md
│   ├── 01_项目范围说明.md
│   ├── 02_需求分析.md
│   ├── 03_系统架构与流程图.md
│   ├── api-contract.md          # API 契约（唯一事实源之一）
│   └── 字段映射表.md
├── backend/                     # Flask 后端（章新怡）
├── miniprogram/                 # 小程序（管理端+志愿者端，赵梓嫣）
├── screenshots/                 # 演示截图
└── presentation/                # 答辩 PPT / 讲稿 / 录屏
```

> 数据库文件 `*.db` 由 `init_db.py` + `seed.py` 生成，**不提交到 Git**（见 `.gitignore`）。

## 3. 当前仓库状态

当前仓库已包含数据库 V1.2、演示数据、数据库查询与项目文档；`backend/` 和 `miniprogram/` 目前只有目录占位文件，Flask API 与小程序页面尚未实现。下文的后端及小程序步骤是目标运行方式，需等相应入口文件完成后再执行。

## 4. 环境依赖

- Python 3.11+（Flask、sqlite3，标准库即可）
- 微信开发者工具（导入 `miniprogram/`；联调时按实施方案启用"不校验合法域名、web-view、TLS 及 HTTP 请求"）
- 运行设备/服务器时区配置为 **Asia/Shanghai**

## 5. 初始化数据库

```bash
# (1) 初始化数据库（在 database/ 目录执行）
cd database
python init_db.py        # 执行 schema.sql 建表
python seed.py           # 灌入演示数据（生成 sports_volunteer.db）

# (2) 跑一遍约束自检（可选）
python test_constraints.py

# 数据库脚本验证完成后，再由后端负责人补充启动命令。
```

`test_constraints.py` 可在 `database/` 目录执行。演示账号仅用于本地样例数据，禁止用于真实部署。

## 6. 演示账号

| 端 | 账号 | 密码 | 说明 |
|---|---|---|---|
| 管理端 | admin_zhongwang | admin123 | 登录后 role=admin |
| 管理端 | scheduler_li | sched123 | 第二个管理员 |
| 志愿者端 | 学号（如 20260001） | 学号后六位（如 260001） | 登录后 role=volunteer |

## 7. 协作与文件所有权

| 成员 | 负责 | 目录 |
|---|---|---|
| 赵梓嫣 | 小程序页面与样式（管理端+志愿者端） | `miniprogram/` |
| 章新怡 | Flask 与 routes | `backend/` |
| 张照锐 | schema / seed / ER / 查询 | `database/` |
| 刘腾罡 | docs / README / report / presentation 与最终合并 | `docs/`, `presentation/` |

**分支**：`feature/frontend-zhao`、`feature/backend-zhangxy`、`feature/database-zhangzr`、`docs/analysis-liu`。
**协作流程**：各成员在自己的分支提交，通过 Pull Request 合并到 `main`；由刘腾罡审阅并负责最终合并。
**提交规范**：`feat:` / `fix:` / `test:` / `docs:`，避免使用 `update`、`最终版` 等含义不清的标题。
**规则**：结构性修改先同步团队；改动 schema 或 API 前先更新 `docs/` 文档。

## 8. 常见问题

- **外键不生效**：sqlite3 连接后执行 `PRAGMA foreign_keys = ON`（`init_db.py` 已包含）。
- **时间差 8 小时**：确认设备时区为 Asia/Shanghai；默认值已用 `datetime('now','localtime')`。
- **小程序请求失败**：优先检查开发者工具"不校验合法域名"是否勾选。
- **重跑演示**：在 `database/` 目录删除 `sports_volunteer.db` 后，重新执行本页初始化步骤。
- **改 CHECK 约束失败**：SQLite 不支持 ALTER 改 CHECK，须重建表——所以 schema 必须一次性写定。
