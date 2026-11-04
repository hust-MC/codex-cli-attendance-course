# 指尖打卡 2.0 · Codex CLI 实战案例

《AI 编程 2.0 革命：Codex CLI 终端智能体实战课》主案例仓库。

用 Codex CLI 从零构建一个可运行的考勤异常闭环平台：员工打卡 → 请假加班 → 日考勤核算 → 异常申诉 → 主管审批 → 月度报表。

技术栈刻意保持最小：Python 3.10+、Flask 3、SQLite 3、原生 HTML/CSS/JS、Python 标准库 `unittest`，不引入 ORM 和前端框架。

## 当前进度

| 章节 | 状态 | 产出 |
|---|---|---|
| 第二章 环境与最小可跑版 | 已完成 | 员工、签到签出、考勤工作台页面 |
| 第三章 Agent 批量开发 | 已完成 | 请假、加班、审批流转，前端两个管理面板 |
| 第四章 AGENTS 与上下文 | 已完成 | 根目录 `AGENTS.md` 与规范一致性核对 |
| 第五章 五阶提示词与 TDD | 待开始 | `tests/` 单元测试与一键验收脚本 |
| 第六章 MCP 与 Skill | 待开始 | SQLite 巡检 MCP 与自定义考勤 Skill |
| 第七章 主案例闭环 | 待开始 | 日核算、异常、申诉、审批、月报 |
| 第八章 遗留代码重构 | 待开始 | 规则抽取与重构前后回归对比 |
| 第九章 多 Agent 协作 | 待开始 | 编码、测试、前端、评审四路分工 |
| 第十章 自动化与交付 | 待开始 | 一键验证、日报、提交说明 |

## 快速开始

```bash
pip install -r requirements.txt
python3 app.py                  # 启动后访问 http://localhost:3000
bash scripts/smoke-api.sh       # 26 项接口冒烟，使用临时数据库和临时端口
```

## 目录说明

| 目录 | 内容 |
|---|---|
| `course/` | 课程设计、项目确认单、章节计划和录制用 Prompt |
| `course/prompts/` | 每章两版录制 Prompt：Codex CLI 版和 DeepSeek 版 |
| `build-log/` | 真实开发记录，按章节归档，含报错和讲解点 |
| `models/` `services/` `routes/` | 数据模型、业务服务、HTTP 路由三层结构 |
| `templates/` `static/` | 服务端模板与原生前端资源 |
| `scripts/` | 接口冒烟与后续演示数据、验收脚本 |
| `AGENTS.md` | 项目级开发规范，也是 Codex 在本仓库的默认上下文 |

## 两条约定

- **规范进 `AGENTS.md`，业务进任务 Prompt**：稳定的工程约束不重复声明，每轮 Prompt 只写增量。
- **记录真实过程**：每章的 Prompt、命令、报错和修复都原样保留在 `build-log/`，不补造失败。

## 核心原则

- 一个项目贯穿全课，不切换案例。
- 每章都有可运行增量，不做只讲概念的章节。
- 录制时可以直接复用阶段 Prompt，并用阶段快照兜底。
