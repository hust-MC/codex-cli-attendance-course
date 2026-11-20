# AGENTS.md

> 本文件是“指尖打卡 2.0”的项目级开发规范，也是 Codex 在本仓库工作时的默认上下文。
> 任务 Prompt 只描述本轮增量，稳定约束统一放在本文件中维护。

## 0. 使用方式

- 开始任何开发任务前，先阅读本文件，再检查当前目录、相关模块和测试。
- 本文件是项目默认约束；具体任务 Prompt 只补充本轮目标、范围和验收标准。
- 如果用户当轮指令与本文件冲突，以用户当轮明确指令为准，并在阶段记录的 `notes.md` 中说明偏差。
- 不确定业务规则时先询问，不要自行扩大需求或引入未讨论的技术方案。
- 修改代码时保持最小变更，不顺手重构无关模块。

## 1. 项目简介

### 项目名称

指尖打卡 2.0：考勤异常闭环平台。

### 一句话定位

一个轻量但完整的员工考勤系统，重点展示从原始打卡数据到异常申诉、审批和月度结算的完整业务闭环。

### 用户角色

- 员工：打卡、提交请假和加班、查看异常、发起申诉。
- 主管：查看团队考勤、审批请假和加班、处理异常申诉、查看月报。
- 本课程暂不实现正式登录鉴权，前端通过员工视角和管理员视角切换来演示流程。

### 核心业务闭环

```text
员工打卡
   |
   v
日考勤核算
   |
   +--> 正常
   +--> 请假
   +--> 迟到 / 早退 / 缺卡 / 缺勤
             |
             v
          员工申诉
             |
             v
          主管审批
             |
       +-----+-----+
       |           |
     通过         驳回
       |           |
       v           v
   冲销异常     异常维持
             |
             v
          月度报表
```

## 2. 课程目标

- 演示 Codex 从空目录完成一个真实业务项目，而不是只生成零散示例。
- 演示项目规范、分阶段 Prompt、自动测试、错误修复和多 Agent 协作。
- 每个阶段都要留下可运行代码、真实 Prompt、命令、日志、测试结果和讲解点。
- 最终产物必须能独立启动、演示和验收，不依赖录制现场的人工补代码。

## 3. 技术栈

- Python 3.10+。
- Flask 3。
- SQLite 3，使用 Python 标准库 `sqlite3`。
- 原生 HTML、CSS、JavaScript。
- Python 标准库 `unittest`。
- Node.js 24+，第六章起用于 MCP 服务器，只用内置模块，不装 npm 包。
- Git 用于阶段快照和差异对比。

### 技术约束

- 不引入 ORM、前端框架或额外运行时依赖，除非用户明确同意。
- 不修改 `requirements.txt` 中已有依赖的版本。
- 测试和演示必须可以在本机离线运行。
- 默认端口为 `3000`，默认数据库为项目根目录下的 `checkin.db`。
- MCP 服务器一律只读打开数据库，且 stdout 只输出 JSON-RPC，日志走 stderr。

### 常用命令

```bash
pip install -r requirements.txt
python3 app.py
python3 scripts/seed-demo.py         # 重置并写入固定演示数据
bash scripts/smoke-api.sh            # 接口冒烟
python3 -m unittest discover -s tests -v
bash scripts/test-mcp.sh             # MCP 服务器协议与业务检查
bash scripts/verify.sh               # 一键验收
```

其中 `scripts/smoke-api.sh` 是接口冒烟脚本，使用临时数据库和临时端口。
`scripts/test-mcp.sh` 是 MCP 服务器的协议与业务检查，用手工 JSON-RPC 探针直接测服务器，不经过 Codex。
`scripts/verify.sh` 依次执行语法编译、代码风格、单元测试、接口冒烟、页面可达性和 MCP 服务器六组检查。
`scripts/seed-demo.py` 生成固定演示数据，避免录制时因历史数据导致结果漂移。

## 4. 目录规范

以下是本项目完成后的目标结构。当前工作区已经有 `models/`、`services/`、`routes/`、`static/`、`scripts/` 和 `build-log/`，`tests/` 属于第五章，`templates/` 用于服务端渲染页面，`mcp/` 和 `.codex/` 属于第六章。

```text
.
├── app.py                  # Flask 应用入口
├── db.py                   # SQLite 连接、建表、索引和初始化
├── requirements.txt        # Python 依赖
├── AGENTS.md               # 项目级开发规范
├── models/                 # 数据结构和接口序列化
├── services/               # 业务规则、状态流转和数据库访问
├── routes/                 # HTTP 路由、参数接收和响应
├── templates/              # 服务端渲染的页面模板
├── static/                 # 原生前端页面、样式和脚本
├── tests/                  # 单元测试和接口测试
├── scripts/                # 验收、演示数据和自动化脚本
├── mcp/                    # MCP 服务器、配置模板和演示数据
├── .codex/skills/          # 项目级 Skill
├── course/                 # 课程设计、讲义和录制素材
└── build-log/              # 真实开发过程归档
```

### 目录职责

| 目录 | 职责 | 禁止事项 |
|---|---|---|
| `routes/` | 接收 HTTP 请求、读取参数、调用 service、返回统一响应 | 禁止直接写 SQL，禁止承载复杂业务规则 |
| `services/` | 参数业务校验、状态机、事务和数据库访问 | 禁止依赖 Flask 请求对象 |
| `models/` | 数据类、查询结果转换和 API 序列化 | 禁止写数据库查询 |
| `db.py` | 连接、建表、索引和幂等初始化 | 禁止放具体业务接口 |
| `templates/` | 服务端渲染的页面模板 | 禁止在模板里写业务规则 |
| `static/` | 页面、样式和浏览器交互 | 禁止把业务规则只写在前端 |
| `tests/` | 自动化测试和测试辅助工具 | 禁止连接正式数据库 |
| `scripts/` | 固定演示数据、验收和自动化任务 | 禁止绕过 service 直接改业务数据 |
| `mcp/` | MCP 服务器、配置模板、外部工具演示数据 | 禁止以写模式打开数据库，禁止往 stdout 打日志 |
| `.codex/skills/` | 项目级 Skill，规定专项任务的执行口径 | 禁止与 `AGENTS.md` 冲突，禁止写入密钥 |
| `build-log/` | 保存真实开发过程 | 禁止补写虚构 Prompt 或测试结果 |

## 5. 分层与调用规则

### 调用方向

```text
HTTP 请求 -> routes -> services -> db / models
                 |
                 v
              统一响应
```

- 路由函数只负责 HTTP 层：读取 JSON、查询参数和路径参数，调用 service，返回响应。
- 业务校验必须放在 service 层，不能只依赖前端校验。
- 所有 SQL 统一放在 `services/` 或 `db.py` 中，并只通过 `get_db()` 获取连接。
- `models/` 只负责数据结构、`from_row()` 和 `to_dict()`，不执行 SQL。
- service 之间可以复用业务方法，但禁止形成循环依赖。
- 业务异常使用统一 `ServiceError` 类型，由全局异常处理器转换为标准响应。
- 所有写操作必须显式 `commit()`；出现异常时回滚并关闭连接。
- 查询必须使用参数化 SQL，禁止字符串拼接用户输入。

### API 响应流

```text
正常请求 -> service 返回模型或数据 -> routes 包装成功响应
业务错误 -> ServiceError -> 全局异常处理器 -> 统一错误响应
未知异常 -> 500 处理器 -> 统一错误响应
```

## 6. 编码规范

### 通用规范

- 所有代码必须添加中文注释；注释解释“为什么”，不要机械翻译代码。
- 每行代码不超过 120 个字符。
- 不使用无意义缩写，不留下调试输出、临时文件和死代码。
- 不吞异常，不使用空的 `except`。
- 公共常量集中定义，避免在多个文件中散落魔法字符串和魔法数字。
- 用户输入必须校验类型、长度和业务状态，错误信息要能指导调用方修正。

### Python 规范

- 函数名使用 `snake_case`，类名使用 `PascalCase`，常量使用 `UPPER_SNAKE_CASE`。
- 模块和函数保持单一职责，单个函数优先控制在 50 行以内。
- 日期使用 `YYYY-MM-DD`，时间使用 `YYYY-MM-DD HH:MM:SS`。
- 时间以 `Asia/Shanghai` 为业务时区，数据库默认使用本地时间。
- 查询结果使用 `sqlite3.Row`，再通过模型转换为字典。
- 新增依赖前必须先确认标准库无法完成。

### JavaScript 规范

- 禁止使用 `var`，统一使用 `const` / `let`。
- 所有接口调用统一经过 `request()` 封装，不在页面中散落错误处理。
- 用户数据写入 DOM 时必须转义（统一用 `escapeHtml`）或使用 `textContent`，避免 XSS 风险。
- 页面必须处理加载中、空数据、成功和失败四种状态。

## 7. API 规范

### 基础约定

- API 前缀统一为 `/api`。
- 请求和响应统一使用 JSON。
- 成功响应 HTTP 状态码为 200，响应体格式固定：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {}
}
```

- 失败响应同时设置 HTTP 状态码和响应体 `code`：
  - `400`：参数错误、业务规则不满足、重复操作。
  - `404`：员工、请假、异常等资源不存在。
  - `405`：请求方法不支持。
  - `500`：未预期服务器错误。
- 错误响应统一为：

```json
{
  "code": 400,
  "message": "员工编号已存在",
  "data": null
}
```

- 列表接口统一返回 `{"total": 0, "items": []}`，不使用裸数组。
- 资源编号使用路径参数，例如 `/api/employees/1`。
- 筛选参数使用 query string，例如 `/api/employees?department=研发部&status=active`。
- 时间筛选参数统一使用 `YYYY-MM-DD`。
- 接口错误信息使用中文，面向课程演示和业务用户。

### 已实现接口

第二章最小可跑版和第三章申请审批已经实现。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/employees` | 新增员工 |
| GET | `/api/employees` | 员工列表和筛选 |
| GET | `/api/employees/<id>` | 员工详情 |
| PUT | `/api/employees/<id>` | 修改员工 |
| DELETE | `/api/employees/<id>` | 逻辑离职 |
| POST | `/api/checkins/in` | 上班签到 |
| POST | `/api/checkins/out` | 下班签出 |
| GET | `/api/checkins` | 按员工和日期查询打卡 |
| POST | `/api/leaves` | 提交请假申请 |
| GET | `/api/leaves` | 请假列表和筛选 |
| GET | `/api/leaves/<id>` | 请假详情 |
| POST | `/api/leaves/<id>/approve` | 审批通过请假申请 |
| POST | `/api/leaves/<id>/reject` | 驳回请假申请 |
| POST | `/api/overtimes` | 提交加班申请 |
| GET | `/api/overtimes` | 加班列表和筛选 |
| GET | `/api/overtimes/<id>` | 加班详情 |
| POST | `/api/overtimes/<id>/approve` | 审批通过加班申请 |
| POST | `/api/overtimes/<id>/reject` | 驳回加班申请 |

### 后续接口模块

| 模块 | 路由前缀 | 说明 |
|---|---|---|
| `attendance` | `/api/attendance` | 日核算和月度报表 |
| `exceptions` | `/api/exceptions` | 考勤异常、申诉和审批 |
| `stats` | `/api/stats` | 首页统计和部门汇总 |

## 8. 数据库规范

### 基础规则

- 默认数据库文件：项目根目录 `checkin.db`。
- 测试和演示可通过 `CHECKIN_DB_PATH` 环境变量切换数据库。
- 所有建表和索引初始化必须幂等，重复执行 `init_db()` 不报错。
- 原始业务数据与计算结果分表保存，不覆盖原始打卡记录。
- 数据库连接必须开启 `PRAGMA foreign_keys = ON`。
- 所有唯一性、状态和类型约束尽量同时在数据库层和服务层落实。
- 数据库结构变更必须同步更新测试和 `course/project-brief.md`。

### 核心业务表

| 表 | 作用 | 关键字段 |
|---|---|---|
| `employees` | 员工主数据 | id, name, department, employee_no, phone, status |
| `checkins` | 原始打卡记录 | employee_id, check_type, check_time, location, remark |
| `leaves` | 请假申请 | leave_type, start_date, end_date, days, reason, status, approver, approve_comment |
| `overtimes` | 加班申请 | work_date, hours, reason, status, approver, approve_comment |
| `attendance_days` | 日核算结果 | work_date, first_in, last_out, late_minutes, early_minutes, status |
| `attendance_exceptions` | 异常和申诉 | exception_type, status, appeal_reason, approver, resolution |
| `audit_logs` | 关键操作审计 | action, entity_type, entity_id, operator, detail |

其中 `attendance_days`、`attendance_exceptions`、`audit_logs` 属于第七章，尚未创建；`attendance_days` 和 `attendance_exceptions` 的字段以实际建表为准，规范先于代码。

### 关键约束

- `employees.employee_no` 唯一，离职采用 `status = 'quit'`，不物理删除。
- `employees.status` 只能是 `active` 或 `quit`。
- `checkins.check_type` 只能是 `in` 或 `out`。
- 同一员工同一天同类型打卡只能有一条，业务层和数据库唯一索引双重保证。
- `checkins.check_time` 使用本地时间字符串，查询时按日期比较。
- `leaves.leave_type` 只能是 `事假`、`病假`、`年假`、`调休`。
- `leaves` 和 `overtimes` 的状态只能是 `pending`、`approved`、`rejected`。
- `attendance_days` 对 `(employee_id, work_date)` 唯一。
- `attendance_exceptions` 对 `(employee_id, work_date, exception_type)` 唯一。
- 异常状态只能是 `open`、`appealed`、`approved`、`rejected`。

## 9. 核心业务规则

### 考勤规则

以下规则属于第七章，目前代码中还没有实现，属于规范先行。

- 上班时间：`09:00`。
- 下班时间：`18:00`。
- 迟到宽限：5 分钟。
- 早退宽限：5 分钟。
- 工作日：周一至周五。
- 已审批全天请假：不生成迟到、早退和缺勤异常。
- 同一天重复签到、重复签出：拒绝。
- 没有签到直接签出：拒绝。
- 缺上班卡、缺下班卡分别生成对应异常。
- 全天无打卡且无请假：生成缺勤异常。

### 请假规则

- 开始日期不能晚于结束日期。
- 同一员工的请假日期不能与已审批请假冲突。
- 请假审批状态只允许从 `pending` 流转到 `approved` 或 `rejected`。
- 已处理的审批不能重复处理。

### 加班规则

- 加班日期必须是有效日期，加班时长必须大于 0 且不超过 24 小时。
- 加班审批状态只允许从 `pending` 流转到 `approved` 或 `rejected`。
- 重复处理已审批记录返回参数错误。

### 异常状态机

以下状态机属于第七章，目前代码中还没有实现。

```text
open -> appealed -> approved
                 -> rejected
```

- `open`：系统生成，等待员工处理。
- `appealed`：员工已提交申诉，等待主管处理。
- `approved`：申诉通过，异常冲销。
- `rejected`：申诉驳回，异常维持。
- 只有 `open` 可以申诉，只有 `appealed` 可以审批。
- 日核算重复执行必须幂等，不能覆盖已经进入申诉流程的异常状态。

### 考勤巡检口径

以下口径属于第六章，已经由 `mcp/attendance-server/server.js` 固化在工具里，
第六章之后的任何巡检都必须复用这些口径，不得另起一套。

- **缺下班卡**：某员工当天有 `check_type = 'in'` 的打卡，但没有 `check_type = 'out'`。
  既没有上班卡也没有下班卡的员工属于"缺勤"，不属于"缺下班卡"，
  缺勤由第七章日核算负责。
- **待审批请假**：`leaves.status = 'pending'` 的申请。
- **重复打卡**：同一员工、同一天、同一打卡类型出现多条记录。
  由于唯一索引在写入阶段已经拦截，正常情况恒为 0 条。
  0 条的含义是"约束生效"，不是"没查到问题"。
- **默认日期**：查询日期不指定时，取数据库里最新的打卡日期，
  不使用系统当天日期，避免演示数据固定而结果漂移。
- **结果限量**：每次查询默认最多 50 条，硬上限 200 条。

### 演示数据

- 演示日期必须固定，避免录制时因系统日期变化导致结果漂移。
- 固定演示案例包括正常、迟到早退、缺下班卡、请假和缺勤。
- 演示数据由 `scripts/` 中的脚本生成，不手工修改正式数据库。

## 10. 前端规范

- 页面使用原生 HTML、CSS 和 JavaScript，不引入前端框架。
- 页面至少覆盖：首页概览、打卡、员工管理、请假、加班、异常中心和月报。
  当前已实现概览、打卡、员工、请假、加班，异常中心和月报属于第七章。
- 所有界面文案使用中文，操作结果必须有明确反馈。
- 表单提交前做基础前端校验，但业务校验必须以后端为准。
- 前端不能假设接口永远成功，必须展示后端返回的错误信息。
- 页面布局必须支持常见桌面和移动端宽度。
- 不把员工数据、异常状态等业务规则硬编码在前端。

## 11. 测试规范

- 使用 Python 标准库 `unittest`。
- 测试文件放在 `tests/`，文件命名为 `test_*.py`。
- 测试使用临时数据库，通过 `CHECKIN_DB_PATH` 隔离，不能污染 `checkin.db`。
- 每个测试用例开始前清理业务数据，避免用例之间相互影响。
- 必须覆盖正常流程、参数错误、资源不存在、重复操作和状态非法流转。
- 日核算和报表类功能必须增加幂等性测试。
- 修复 Bug 时先补回归测试，再修复实现。
- 不允许通过删除断言、跳过测试或降低覆盖范围来让测试通过。
- 写测试前先确认服务层函数的真实名字和签名，不要凭直觉命名。
- 测试用例的预期必须基于真实业务规则。测试失败时先判断是实现有 Bug
  还是断言写错，确认后再动手，不要直接改断言让它变绿。
- 造数辅助方法统一放在 `tests/base.py`，不要在每个用例里重复写插入语句。
- 阶段结束必须运行：

```bash
python3 -m unittest discover -s tests -v
bash scripts/verify.sh
```

## 12. 开发记录规范

每个可运行阶段都必须同步更新 `build-log/`，至少包含：

- `prompt.md`：本轮实际下达的任务 Prompt。
- `commands.log`：实际执行的关键命令。
- `test.log`：原始测试输出。
- `smoke.log`：真实 HTTP 或页面验收输出。
- `errors.log`：真实报错和失败记录，没有失败时明确写“无失败记录”。
- `result.md`：完成内容、限制和下一步。
- `notes.md`：架构判断和录课讲解点。

### 记录原则

- 不伪造 Prompt、命令、测试输出或修复过程。
- 失败记录不能被最终成功日志覆盖。
- 录制版 Prompt 在实际开发完成后从真实记录中提炼，不反向编造。
- 课程讲解必须能够对应到真实文件、命令和运行结果。

## 13. Git 规范

- commit 格式：`type: 描述`。
- `type` 只使用 `feat`、`fix`、`chore`、`docs`。
- 每个可运行阶段保持一次清晰提交，提交内容包含代码、测试和必要文档。
- 不在提交中混入数据库文件、缓存文件、临时日志和本地密钥。
- 未经用户明确要求，不执行 commit、amend、rebase、force push 或创建分支。
- 当前工作区还不是 Git 仓库，初始化仓库后本节才生效；第八、九章依赖 Git 做快照和分支对比。

## 14. 范围边界

以下内容不属于本课程主案例范围，除非用户明确变更需求：

- 真实工资核算和财务结算。
- GPS、Wi-Fi、人脸识别等真实定位或身份验证。
- 复杂排班、多班次和跨时区考勤。
- 正式 JWT、单点登录和组织权限体系。
- 短信、邮件、企业微信等外部通知。
- 云部署、容器编排和真实线上运维。

## 15. 完成定义

一个阶段只有同时满足以下条件才算完成：

- 代码可以从当前工作区直接启动。
- 本轮新增和修改的接口有自动化测试。
- `python3 -m unittest discover -s tests -v` 全部通过。
- 至少完成一次真实 HTTP 或页面冒烟验证。
- 没有未处理的相关回归问题。
- `build-log/` 已保存真实 Prompt、命令、结果和讲解点。
- 最终回复明确列出完成内容、验证方式、限制和下一步。
