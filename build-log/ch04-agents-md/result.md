# 第四章结果：AGENTS.md 落地

## 完成内容

- `course/agents-md-draft.md` 复制为根目录 `AGENTS.md`，作为项目默认上下文。
- 逐条核对规范与代码，修掉 6 处不一致，细节见 `consistency-check.md`。
- 未实现的部分（第七章的三张表和考勤规则、第五章的测试、异常中心与月报页面）在规范里明确标注归属章节。
- 补充 `course/prompts/ch04/codex.md` 和 `course/prompts/ch04/deepseek.md`，作为第四章的两版录制用 Prompt。

## 验证方式

- `bash scripts/smoke-api.sh`：26 项接口冒烟全部通过，说明规范改动没有影响现有行为。
- 规范改动只涉及文档，不涉及运行逻辑。

## 关键结论

规范和代码之间天然会漂移。这一轮就找出 6 处：3 处内容写错，3 处状态没标注。

第四章要讲的不是「写一份 AGENTS.md」，而是「规范要跟着代码一起维护」。这句话背后就是这 6 处不一致。

## 当前限制

- `AGENTS.md` 还没有在真实的 Codex CLI 会话里验证过效果，录制时必须先跑一次短 Prompt，确认它真的会读。
- 规范里「考勤规则」目前是纯纸面规则，第七章实现后要回头再核对一次。

## 下一步

- 第五章：补 `tests/` 单元测试和 `scripts/verify.sh` 一键验收，验证「测试约束 AI」这条主线。
