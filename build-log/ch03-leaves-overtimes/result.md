# M1 结果说明：请假、加班与审批

## 完成内容

- 新增 `leaves` 表：请假类型、起止日期、天数、审批状态、审批人和审批意见。
- 新增 `overtimes` 表：加班日期、时长、审批状态、审批人和审批意见。
- `employees` 表补 `phone` 和 `status` 字段，员工删除改为逻辑离职，历史考勤数据保留。
- `checkins` 表补 `location` 和 `remark` 字段，与项目规范保持一致。
- 新增 `models/leave.py`、`models/overtime.py`、`services/leave_service.py`、`services/overtime_service.py`。
- 新增 `services/validators.py`，把参数解析从 `employee_service` 里抽出来共用。
- 新增 `routes/leaves.py`、`routes/overtimes.py`，共 10 个接口。
- 前端新增请假管理、加班管理两个面板，含状态筛选、提交弹窗、通过与驳回操作。
- 新增 `scripts/smoke-api.sh`，一条命令跑完 26 项接口冒烟，使用临时数据库和临时端口。
- `app.py` 支持用 `PORT` 环境变量覆盖端口。

## 实际接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/leaves` | 提交请假申请 |
| GET | `/api/leaves` | 请假列表，支持 employee_id / status / start_date / end_date 筛选 |
| GET | `/api/leaves/<id>` | 请假详情 |
| POST | `/api/leaves/<id>/approve` | 审批通过 |
| POST | `/api/leaves/<id>/reject` | 驳回 |
| POST | `/api/overtimes` | 提交加班申请 |
| GET | `/api/overtimes` | 加班列表，筛选参数同上 |
| GET | `/api/overtimes/<id>` | 加班详情 |
| POST | `/api/overtimes/<id>/approve` | 审批通过 |
| POST | `/api/overtimes/<id>/reject` | 驳回 |
| GET | `/api/employees?status=active` | 按在职状态筛选员工 |

## 业务规则落点

- 请假类型只能是事假、病假、年假、调休。
- 开始日期不能晚于结束日期，天数按包含首尾两天计算。
- 与已审批请假日期区间重叠的申请被拒绝。
- 加班时长必须大于 0 且不超过 24 小时，同一员工同一天只能有一条加班申请。
- 请假和加班的审批状态只能从 `pending` 流转一次，重复审批返回 400。
- 离职员工不能打卡、不能提交申请，离职后历史数据仍然保留。

## 验证结果

- `bash scripts/smoke-api.sh`：26 项全部通过。
- 静态检查：Python 编译通过，所有代码行宽不超过 120 字符，`routes/` 目录没有 SQL。
- 页面验收：请假和加班两个面板正常渲染，UI 上点击「通过」后状态和待审批数量同步刷新。

## 当前限制

- 没有自动化测试用例，`scripts/smoke-api.sh` 覆盖的是接口层，单元测试属于第五章。
- 审批人是前端写死的「人事主管」，项目明确不实现真实登录鉴权。
- 请假冲突只和「已审批」记录比较，待审批的重叠申请目前允许提交。
- 加班没有对应的考勤联动，核算时如何抵扣工时属于第七章。
- 演示数据还没有固定脚本，固定数据脚本属于第七章。

## 下一步

- 第四章：把 `course/agents-md-draft.md` 落到项目根目录作为 `AGENTS.md`，验证长短 Prompt 的效果差别。
- 第五章：补 `tests/` 单元测试和 `scripts/verify.sh` 一键验收。
