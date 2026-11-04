# 第四章验证：一条短 Prompt，AGENTS.md 到底生不生效

这是第四章的验收动作，用真实 Codex CLI 跑，不是演示。

## 验证环境

- Codex CLI：`codex-cli 0.166.0`，配置的后端是 DeepSeek（`~/.codex/config.toml` 里 `model = "deepseek-v4-flash"`）。
- 隔离方式：`git worktree add /tmp/ch04-verify -b verify/agents-md`，不动主分支。
- 执行命令：`codex exec --sandbox workspace-write -C /tmp/ch04-verify -`，Prompt 从标准输入喂进去。

## 用的 Prompt（短 Prompt，一个字没多）

```text
请阅读并遵守根目录 AGENTS.md。

本轮实现打卡地点和备注：签到签出时允许传入 location 和 remark 两个可选参数，
存进 checkins 表已有的字段里，并在查询打卡记录时返回。

只做这一件事，完成后跑一次接口自测。
```

## 任务怎么选的

不是编一个玩具任务。项目里 `checkins` 表和 `Checkin` 模型本来就有 `location` 和 `remark` 两个字段，但签到签出接口从来不接收它们——是一个真实的、长期存在的缺口。

选它的原因：任务小、边界清楚，但**恰好会踩到 `AGENTS.md` 的多条规则**——路由层不写 SQL、参数校验放 service、复用公共校验函数、响应格式、注释和行宽。

## 逐条核对结果

| `AGENTS.md` 里的规则 | Codex 是否遵守 | 证据 |
|---|---|---|
| 路由层不写 SQL | 遵守 | `routes/` 目录零改动，业务逻辑全在 `services/checkin_service.py` |
| 业务校验放 service 层 | 遵守 | 新增的 `location`、`remark` 校验写进了 service，没有进路由 |
| 复用项目已有工具 | 遵守 | 直接 `from services.validators import clean_text`，没有自己重写一遍 |
| 公共常量集中定义 | 遵守 | 新建 `MAX_LOCATION_LENGTH` / `MAX_REMARK_LENGTH` 常量，没有散落魔法数字 |
| 中文注释 | 遵守 | 新增了「打卡地点和备注仅用于补充业务信息……」的说明性注释 |
| 每行不超过 120 字符 | 遵守 | `awk 'length>120'` 检查两个文件，零行超限 |
| 参数化 SQL | 遵守 | 仍然是 `VALUES (?, ?, ?, ?, ?)` 占位符 |
| 空值处理一致 | 遵守 | 空字符串统一转成 `NULL`，和表结构对得上 |

**结论：8 条规则全部遵守，一条没漏。** 这就是第四章要证明的事——规范写下来，模型真的照做。

## 它自己加的东西

Codex 主动给 `scripts/smoke-api.sh` 补了 6 条断言：

- 新增 `expect_data_field()` 辅助函数，支持 `records.0.location` 这种路径访问
- 签到、签出改成带 `location` 和 `remark` 的请求
- 补了「重复签出」用例
- 补了「查询返回签到地点」「查询返回签到备注」两条字段级断言
- 补了「不传可选参数时返回 null」的用例

脚本从 26 项变成 32 项，在真实环境跑全部通过。

## 一条没遵守的：没建 `tests/`

`AGENTS.md` 第 11 节明确写了「测试文件放在 `tests/`，文件命名为 `test_*.py`」，第 15 节完成定义也写了「本轮新增和修改的接口有自动化测试」。

Codex **没有创建 `tests/` 目录**，而是自己写了一段临时的 Flask `test_client` 脚本跑完就删了。

原因分析：`tests/` 目录当时根本不存在，`AGENTS.md` 里提到的 `bash scripts/verify.sh` 也不存在。模型看到的是一个「规范提到了、但仓库里没有」的目标，倾向于绕开而不是补齐。

这条反而是第四章最有价值的教学点：

> **规范里写了一个仓库里还不存在的东西，模型会绕过它，而不是替你补上。**

两个处理办法：
1. 规范只写已经存在的东西，测试要求等 `tests/` 建好之后再写进规范（第五章）。
2. 或者提前把 `tests/` 建出来，让规范有落点。

这直接说明「规范要先于代码写」是有代价的，规范里的每一条都应该对应仓库里真实存在的东西。

## 另一个真实记录：沙箱里跑不了端口绑定

Codex 在沙箱内执行 `scripts/smoke-api.sh` 时失败，报错是 Flask 启动时绑定端口被拒。它没有跳过验证，而是改用 Flask `test_client` 在进程内完成了等价断言，最后如实报告「真实端口冒烟脚本因当前沙箱禁止 TCP 监听而无法运行」。

这句话值得在课上原样念出来——**它没有假装脚本跑通了**，而是区分了「已验证」和「未验证」。

## 归档动作

- worktree 分支 `verify/agents-md` 保留，`git diff` 可复查。
- 本次改动没有合并进 `main`，因为「打卡地点和备注」属于第二章的收尾内容，需要你确认后再合。
