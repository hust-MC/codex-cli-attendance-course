# 录制前演示清单

录制第二章 2.4 和 2.5 之前，把下面每一项亲手跑一遍。全部打过，录制时就不会现场翻车。

每项都写了**预期输出**，对不上就说明环境有问题，先解决再录。

---

## 零、开录前的环境体检（1 分钟）

```bash
cd /Users/chaodikong/Android/codex
bash course/scripts/codex-doctor.sh
```

预期最后一行：

```text
  [PASS] 8 项检查全部通过，环境健康
  通过 7 项，风险 0 项，失败 0 项
```

退出码必须是 `0`。

如果「接口连通性」失败，先解决网络再录，别硬上。

---

## 一、重置演示数据（2 分钟，2.4 开录前必做）

```bash
cd /Users/chaodikong/Android/codex
python3 scripts/seed-demo.py
```

预期输出：

```text
数据库文件： /Users/chaodikong/Android/codex/checkin.db
清空原有业务数据 ...
写入演示员工 ...
写入演示打卡 ...
写入演示请假 ...
写入演示加班 ...

演示数据已就绪：
  员工 5 人（含 1 名已离职）
  打卡 3 条（含 1 条缺下班卡）
  请假 3 条（待审批 / 已通过 / 已驳回各一）
  加班 2 条
```

**为什么每次都要跑**：演示数据固定，录制时不会因为「上次跑过了所以报重复工号」而漂移。

---

## 二、起服务（1 分钟）

```bash
cd /Users/chaodikong/Android/codex
python3 app.py
```

预期：

```text
 * Running on http://127.0.0.1:3000
```

**如果提示 `Address already in use`**，说明有旧实例占着端口：

```bash
lsof -ti:3000 | xargs kill
python3 app.py
```

---

## 三、接口冒烟（1 分钟）

另开一个终端：

```bash
cd /Users/chaodikong/Android/codex
bash scripts/smoke-api.sh
```

预期结尾：

```text
----------------------------------------
通过 26 项，失败 0 项
接口冒烟测试全部通过
```

这个脚本用独立的临时数据库和临时端口，不会动你的 `checkin.db`。

---

## 四、页面演示（2 分钟）

浏览器打开 <http://localhost:3000>，逐个点过去看：

| 页面 | 检查点 |
|---|---|
| 概览 | 员工 5 人（含 1 名已离职），请假 3 条、加班 2 条的状态统计正确 |
| 打卡 | 张三有上下班两条记录，李四只有上班卡（演示缺下班卡） |
| 员工 | 5 名员工，孙七状态是「已离职」 |
| 请假 | 三条状态各一：待审批、已通过、已驳回 |
| 加班 | 两条：待审批、已通过 |

**重点确认浏览器控制台没有红色报错**。

---

## 五、2.4 演示要敲的命令（按顺序，每条都验证过）

这些是 2.4 现场实操要敲的 curl 命令。全部返回预期内容。

```bash
# 1. 健康检查
curl -s http://127.0.0.1:3000/api/health
```
预期：`{"code": 200, "data": null, "message": "服务正常"}`

```bash
# 2. 员工列表
curl -s http://127.0.0.1:3000/api/employees
```
预期：5 名员工，字段含 `id` `name` `department` `employee_no` `phone` `status`

```bash
# 3. 新增员工
curl -s -X POST http://127.0.0.1:3000/api/employees \
  -H 'Content-Type: application/json' \
  -d '{"name":"周八","department":"技术部","employee_no":"E2001","phone":"13900000001"}'
```
预期：`code: 200`，返回带 `id` 的员工对象

```bash
# 4. 重复工号（这是重点，要演示被拦住）
curl -s -X POST http://127.0.0.1:3000/api/employees \
  -H 'Content-Type: application/json' \
  -d '{"name":"周八","department":"技术部","employee_no":"E2001"}'
```
预期：`{"code": 400, "message": "工号已存在"}`

```bash
# 5. 签到（带上地点和备注）
curl -s -X POST http://127.0.0.1:3000/api/checkins/in \
  -H 'Content-Type: application/json' \
  -d '{"employee_id":1,"location":"总部一楼","remark":"准时到岗"}'
```
预期：`code: 200`，并且 `location` 是「总部一楼」、`remark` 是「准时到岗」

> 这一条依赖第四章 `AGENTS.md` 验证时做的那次改动（让签到接受可选的地点和备注）。
> 如果返回的 `location` 是 null，说明改动没合进来，检查 `services/checkin_service.py` 里
> `create_checkin` 是否处理了 `location` 和 `remark`。

**注意**：如果第 5 条报「当天已经签过到了」，说明张三今天已经打过卡——重跑第一步的 `seed-demo.py`。

```bash
# 6. 重复签到（要演示被拦住）
curl -s -X POST http://127.0.0.1:3000/api/checkins/in \
  -H 'Content-Type: application/json' \
  -d '{"employee_id":1}'
```
预期：`{"code": 400, "message": "当天已经签到，不能重复操作"}`

```bash
# 7. 查询打卡记录
curl -s "http://127.0.0.1:3000/api/checkins?employee_id=1"
```
预期：返回 `records` 数组，含 `location` 和 `remark` 字段

```bash
# 8. 提交请假
curl -s -X POST http://127.0.0.1:3000/api/leaves \
  -H 'Content-Type: application/json' \
  -d '{"employee_id":1,"leave_type":"年假","start_date":"2026-11-20","end_date":"2026-11-21"}'
```
预期：`code: 200`，`days: 2`，`status: "pending"`

```bash
# 9. 审批通过
curl -s -X POST http://127.0.0.1:3000/api/leaves/4/approve \
  -H 'Content-Type: application/json' \
  -d '{"approver":"王经理","comment":"同意"}'
```
预期：`code: 200`，`status: "approved"`

> 请假 ID 用 **4**，因为演示数据里已经有 1、2、3 三条。
> 如果不确定，先 `curl -s http://127.0.0.1:3000/api/leaves` 看当前最大 ID。

```bash
# 10. 重复审批（要演示被拦住）
curl -s -X POST http://127.0.0.1:3000/api/leaves/4/approve \
  -H 'Content-Type: application/json' \
  -d '{"approver":"王经理"}'
```
预期：`code: 400`

---

## 六、2.5 演示要跑的命令

### 6.1  Token 用量与预算（1 分钟）

```bash
cd /Users/chaodikong/Android/codex
bash course/scripts/budget-check.sh
```

预期：

```text
  会话线程数：N
  累计 Token：N
  单会话上下文上限：244800
  最长会话占用：N%（N / 244800）
```

然后演示**超支警告**，把预算压到很低：

```bash
BUDGET_LIMIT=0.1 bash course/scripts/budget-check.sh
```

预期结尾：

```text
  [FAIL] 已超预算（用了 NNN%）

  建议立刻执行：
    1. /compact      压缩当前会话上下文
    2. /clear        清空上下文重新开始
    3. 换更便宜的模型继续干剩余任务
```

### 6.2  按会话看上下文占用

```bash
bash course/scripts/budget-check.sh --threads
```

预期：每个会话一行，显示 token 数和占用百分比。

### 6.3  按模型统计

```bash
bash course/scripts/budget-check.sh --by-model
```

预期：按模型名汇总 token 数。

> 三个参数可组合：`--threads`、`--by-model`。
> 数据源是 `~/.codex/logs_2.sqlite`，所以刚跑完的 codex 会话要等日志落盘才看得到。

---

## 七、第四章验证（可选，2 分钟）

演示 `AGENTS.md` 真的生效：

```bash
cd /Users/chaodikong/Android/codex
git worktree add /tmp/ch04-verify -b verify/agents-md
```

然后用短 Prompt 跑 Codex（Prompt 内容见 `course/prompts/ch04/codex.md`）。

录完记得清理：

```bash
cd /Users/chaodikong/Android/codex
git worktree remove /tmp/ch04-verify
git branch -D verify/agents-md
```

---

## 八、录完收尾

```bash
cd /Users/chaodikong/Android/codex
# 恢复干净状态，让下次录制从同一个起点开始
python3 scripts/seed-demo.py
lsof -ti:3000 | xargs kill
git status
```

---

## 演示脚本速查

| 脚本 | 用途 | 用在 |
|---|---|---|
| `course/scripts/codex-doctor.sh` | Codex 环境自诊，8 项 | 2.2、2.3 |
| `course/scripts/budget-check.sh` | Token 用量与预算守护 | 2.5 |
| `scripts/seed-demo.py` | 生成固定演示数据 | 2.4 开录前 |
| `scripts/smoke-api.sh` | 接口冒烟，26 项 | 2.4、2.5 |

## 演示前最后一次体检

```bash
cd /Users/chaodikong/Android/codex
bash course/scripts/codex-doctor.sh && \
python3 scripts/seed-demo.py && \
bash scripts/smoke-api.sh && \
echo "✅ 全部就绪，可以开录"
```
