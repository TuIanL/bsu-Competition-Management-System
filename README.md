# bsu-Competition-Management-System

> 体育赛事志愿者调度系统 · 双端小程序
> 课程项目 · 技术栈：**微信小程序前端 + Flask JSON API + SQLite**
> 项目管理员 / 系统分析员：刘腾罡｜后端 + 前端 + 测试：赵梓嫣（接手原后端分工）｜系统设计/DBA：张照锐

## 1. 项目简介

单个小程序双端：**管理端**由组委会维护志愿者、赛事、岗位与班次并执行调度；**志愿者端**由志愿者
自助查看班次、报名岗位、签到签退、查看志愿时长。系统通过**数据库约束（UNIQUE/CHECK/FK/触发器）+
后端业务层校验**阻止重复调度、时间冲突、超员与重复报名，并实时展示班次名单与缺口统计。

> 定位：报名意向由志愿者提交，**最终排班动作仍由管理员确认执行**。

## 2. 五分钟跑起来

```bash
# 1) 安装后端依赖（只有 Flask）
pip install -r backend/requirements.txt

# 2) 启动后端（首次启动会自动建库并灌入演示数据）
python backend/app.py
#    想把演示数据恢复到初始状态：python backend/app.py --reset-db
```

3) 打开**微信开发者工具** → 导入项目 → 目录选择 `miniprogram/`（AppID 可用测试号，或保持 `touristappid` 游客模式）。
   `project.config.json` 已关闭"校验合法域名"（`urlCheck: false`），不需要再手动勾选。

4) 用演示账号登录（登录页可以点一下自动填入）：

| 端 | 账号 | 密码 | 演示用途 |
|---|---|---|---|
| 管理端 | `admin_zhongwang` | `admin123` | 调度、Dashboard |
| 管理端 | `scheduler_li` | `sched123` | 第二个管理员 |
| 志愿者 | `20260002`（李包房） | `260002` | 今天有进行中的班次，可演示**签到 → 签退** |
| 志愿者 | `20260001`（张礼宾） | `260001` | 已签到可签退；有一个待安排的报名；有 4 小时已完成时长 |
| 志愿者 | 其他学号 `20260001`–`20260020` | 学号后六位 | `20260010`、`20260015` 已停用，无法登录 |

> 手机真机预览：把 `miniprogram/config.js` 的 `BASE_URL` 改成后端启动时打印的局域网地址（手机与电脑同一 WiFi）。

## 3. 演示数据里预设好的场景

种子数据的时间都**相对运行当天**生成，任何一天重置后都能演示：

| 场景 | 怎么演示 | 预期 |
|---|---|---|
| 时间冲突 T09 | 调度页打开"观众服务 午间"（明天 11–15），安排**钱球员** | 拒绝：与"球员服务 明天 09:00–13:00"冲突 |
| 边界不冲突 T10 | 打开"媒体助理 下午"（明天 13–17），安排**钱球员** | 成功（13:00 结束 / 13:00 开始） |
| 满员 T11 | 打开"莲花球场 医疗协助"（2/2），安排任意人 | 拒绝：该班次已满员 |
| 停用 T12 | 任意班次安排**王停用** | 拒绝：该志愿者已停用 |
| 重复报名 | 志愿者 20260001 报名"球员服务"（已报过） | 按钮显示"已报名，待安排" |
| 被拒绝不可再报 | 志愿者 20260020 | 看不到"夜场观众服务" |
| 撤回后可再报 | 志愿者 20260002 | "包房服务"显示"你曾撤回过，可再次报名" |
| 爽约 | 志愿者 20260011 | 一周前班次显示"未签到" |

## 4. 目录结构

```
.
├── database/                 # 数据库（张照锐，V1.3 加固见 data_dictionary.md）
│   ├── schema.sql            # 7 表 + 视图 v_shift_status + 6 索引 + 1 触发器
│   ├── init_db.py / seed.py  # 建库 / 演示数据（任意目录可运行）
│   ├── test_constraints.py   # 15 项约束自检（内存库，不污染数据）
│   ├── core_queries.sql      # 7 条核心查询（与后端实现一致）
│   └── data_dictionary.md / troubleshooting.md / ER图.svg
├── backend/                  # Flask JSON API
│   ├── app.py                # 入口：python backend/app.py
│   ├── core.py               # 数据库连接、统一响应、错误处理、参数校验
│   ├── auth.py               # token 签发与校验、角色装饰器
│   ├── rules.py              # 调度四规则 R1–R4（集中一处）
│   ├── routes/               # 各模块接口
│   └── tests/                # 47 项 pytest 自动化测试
├── miniprogram/              # 微信小程序（管理端 + 志愿者端）
│   ├── config.js             # 后端地址（唯一需要按环境修改的地方）
│   ├── utils/request.js      # 统一请求封装
│   ├── components/           # tab-bar（按角色切换的底部导航）、seat-bar（名额座位格）
│   └── pages/                # login / admin/* / volunteer/* / password
├── docs/                     # 需求、架构、API 契约 v3、字段映射、测试报告、总控台
├── screenshots/              # 演示截图
└── presentation/             # 答辩 PPT / 讲稿 / 录屏
```

## 5. 测试

```bash
pip install -r backend/requirements-dev.txt
python -m pytest backend           # 47 项接口测试：T01–T14 + 志愿者端 + 越权
python database/test_constraints.py  # 15 项数据库约束测试
```

测试用例与结果见 `docs/04_测试报告.md`。

## 6. 协作与文件所有权

| 成员 | 负责 | 目录 |
|---|---|---|
| 赵梓嫣 | 小程序页面与样式 + Flask 后端 + 系统测试 | `miniprogram/`、`backend/` |
| 张照锐 | schema / seed / ER / 查询 | `database/` |
| 刘腾罡 | docs / README / report / presentation 与最终合并 | `docs/`、`presentation/` |

**分支**：`feature/fullstack-zhao`（前后端）、`feature/database-zhangzr`、`docs/analysis-liu`。
**协作流程**：各成员在自己的分支提交，通过 Pull Request 合并到 `main`；由刘腾罡审阅并负责最终合并。
**提交规范**：`feat:` / `fix:` / `test:` / `docs:`，避免使用 `update`、`最终版` 等含义不清的标题。
**规则**：结构性修改先同步团队；改动 schema 或 API 前先更新 `docs/` 文档与测试。

## 7. 常见问题

- **小程序提示"连不上服务器"**：后端是否已启动；`miniprogram/config.js` 地址是否正确；真机预览不能用 127.0.0.1。
- **外键不生效**：sqlite3 连接后执行 `PRAGMA foreign_keys = ON`（后端与脚本均已包含）。
- **时间差 8 小时**：确认电脑时区为 Asia/Shanghai；后端用本机时间。
- **演示数据被改乱**：`python backend/app.py --reset-db`。
- **改 CHECK 约束失败**：SQLite 不支持 ALTER 改 CHECK，须重建表——所以 schema 要一次性写定。
- **Git Bash 里中文乱码**：脚本已统一按 UTF-8 输出；仍有问题可先执行 `export PYTHONIOENCODING=utf-8`。
