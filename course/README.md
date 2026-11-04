# 课程生产目录

本目录只存放与录课直接相关的内容，不承载业务代码。

## 目标

- 把项目开发过程拆成可演示、可验收的阶段。
- 每个阶段保留真实 Prompt、执行日志、测试结果和讲解要点。
- 录制课程时可按阶段复现，而不是只展示最终代码。
- 课程上线后可以继续复用本目录维护讲义、Prompt 和演示数据。

## 文档索引

- `course-map.md`：课程定位、10 章结构与时间分配。
- `project-brief.md`：主案例 PRD、架构、数据和验收标准。
- `staging-and-prompt-log.md`：开发阶段、Prompt 记录和素材归档规范。
- `recording-checklist.md`：录课前、中、后的检查清单。
- `agents-md-and-prompt.md`：AGENTS.md 的内容设计、长短 Prompt 对比和录制话术。
- `agents-md-draft.md`：AGENTS.md 完整草案，第四章录制时再移动到项目根目录。
- `chapter-plan.md`：十章阶段任务、验收标准和 Prompt/Bug 记录节点。

## 命名说明

- `course/` 下的文件使用描述性名称，不再用 `01-`、`02-` 这类前缀，避免被误认为课程章节号。
- 课程章节统一写成“第一章”“第二章”，不缩写为 C01 或 S02。
- `build-log/` 使用 `ch02-minimal`、`ch07-attendance-loop` 这类目录名，`chNN` 明确对应章节编号。
- 同一章如果有多个独立阶段，可以在章节目录下继续建立子目录。

## 后续目录规划

```text
course/
├── course-map.md
├── project-brief.md
├── staging-and-prompt-log.md
├── recording-checklist.md
├── agents-md-and-prompt.md
├── chapter-plan.md
├── chapters/          # 各章节课程稿与分镜
├── prompts/           # 录制版 Prompt
├── slides/            # PPT 提纲与截图资产
└── demo/              # 固定演示数据与演示脚本

build-log/             # 实际开发过程归档
prompts/               # 实际构建项目的 Prompt
snapshots/             # 各阶段快照说明
```
