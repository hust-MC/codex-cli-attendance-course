# build-log 索引

真实开发记录按章节归档，每章一个目录。

| 目录 | 对应章节 | 内容 |
|---|---|---|
| `ch02-minimal/` | 第二章 2.4 | 员工、签到签出最小后端的 Prompt、日志、结果和讲解点 |
| `ch03-leaves-overtimes/` | 第三章 | 请假、加班、审批模块，含 5 条真实报错记录 |
| `ch04-agents-md/` | 第四章 | `AGENTS.md` 落地与规范一致性核对 |

每个目录里的文件按规范固定：

| 文件 | 内容 |
|---|---|
| `prompt.md` | 本轮实际使用的任务 Prompt |
| `commands.log` | 实际执行的关键命令 |
| `test.log` | 原始测试输出 |
| `smoke.log` | 真实 HTTP 或页面验收输出 |
| `static-checks.log` | 编译、行宽、路由层无 SQL 等静态检查 |
| `errors.log` | 真实报错与失败记录，没有就写明 |
| `result.md` | 完成内容、限制和下一步 |
| `notes.md` | 架构判断和录课讲解点 |

录制用 Prompt 在 `course/prompts/`，每章两版：Codex CLI 版和 DeepSeek 版。
