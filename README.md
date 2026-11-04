# Codex 课程项目工作区

本目录用于从零构建《AI 编程 2.0 革命：Codex CLI 终端智能体实战课》的主案例。

## 目录说明

- `course/`：课程设计、项目确认单、录制脚本、Prompt 记录和验收清单。
- `build-log/`：正式录制时的真实开发记录，按章节建立子目录。
- `course/agents-md-draft.md`：AGENTS.md 草案，第四章再放入根目录使用。
- `_archive/`：旧项目和历史预研代码，仅用于隔离保存，新项目不引用。

根目录暂不放置 `AGENTS.md`，避免第二、三章自动读取第四章才讲的规范。

## 当前目录

```text
.
├── README.md             # 工作区说明
├── course/               # 课程设计、章节计划和录制素材
├── build-log/            # 真实开发记录，按章节建立子目录
├── app.py                # Flask 应用入口
├── db.py                 # SQLite 初始化、建表和索引
├── models/               # 数据模型和序列化
├── services/             # 业务规则、状态流转和数据库访问
├── routes/               # API 路由
├── templates/            # 页面模板
├── static/               # 原生 CSS 和 JavaScript
├── scripts/              # 接口冒烟、演示数据和自动化脚本
└── _archive/             # 旧项目和历史预研代码，不参与正式开发
```

## 当前阶段

按「先把案例整个项目跑通，再回头写讲稿」的顺序推进，逐字稿最后再写。

已完成：

- 第二章 2.4：员工、签入签出最小后端，前端考勤工作台，记录在 `build-log/ch02-minimal/`。
- 第三章 M1：请假、加班、审批流转，员工改为逻辑离职，前端增加两个申请与审批面板，记录在 `build-log/ch03-leaves-overtimes/`。
- 第四章：`AGENTS.md` 落到根目录并完成规范与代码的一致性核对，记录在 `build-log/ch04-agents-md/`。

录制用 Prompt 在 `course/prompts/`，每章两版：Codex CLI 版和 DeepSeek 版。

下一步是第五章：补 `tests/` 单元测试和 `scripts/verify.sh` 一键验收。

## 运行方式

```bash
pip install -r requirements.txt
python3 app.py            # 默认端口 3000，可用 PORT 环境变量覆盖
bash scripts/smoke-api.sh # 临时数据库跑 26 项接口冒烟
```

## 核心原则

- 一个项目贯穿全课，不切换案例。
- 每章都有可运行增量，不做只讲概念的章节。
- 每个开发阶段同步记录 Prompt、命令、执行结果、报错和修复过程。
- 录制时可以直接复用阶段 Prompt，并使用阶段快照兜底。
- 课程目标时长约 9 小时，硬上限 10 小时。
