#!/usr/bin/env bash
# 接口冒烟脚本
# 用临时数据库和临时端口跑一遍核心接口，验证接口行为且不污染正式数据库
#
# 用法：
#   bash scripts/smoke-api.sh
#
# 退出码：全部通过为 0，出现失败为 1
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_PORT="${BASE_PORT:-3100}"
BASE_URL="http://127.0.0.1:${BASE_PORT}"

WORK_DIR="$(mktemp -d)"
export CHECKIN_DB_PATH="${WORK_DIR}/smoke.db"
SERVER_LOG="${WORK_DIR}/server.log"

PASS_COUNT=0
FAIL_COUNT=0
RESPONSE_CODE=""
RESPONSE_BODY=""

# 清理临时目录并结束服务
cleanup() {
    if [ -n "${SERVER_PID:-}" ] && kill -0 "${SERVER_PID}" 2>/dev/null; then
        kill "${SERVER_PID}" 2>/dev/null
        wait "${SERVER_PID}" 2>/dev/null
    fi
    rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

# 发起一次请求，结果写入 RESPONSE_CODE 和 RESPONSE_BODY
request() {
    local method="$1"
    local path="$2"
    local body="${3:-}"

    if [ -n "${body}" ]; then
        RESPONSE_BODY="$(curl -s -X "${method}" "${BASE_URL}${path}" \
            -H 'Content-Type: application/json' -d "${body}" -w '\n%{http_code}')"
    else
        RESPONSE_BODY="$(curl -s -X "${method}" "${BASE_URL}${path}" -w '\n%{http_code}')"
    fi

    RESPONSE_CODE="$(printf '%s' "${RESPONSE_BODY}" | tail -n 1)"
    RESPONSE_BODY="$(printf '%s' "${RESPONSE_BODY}" | sed '$d')"
}

# 从响应体中取出 message 字段
extract_message() {
    printf '%s' "${RESPONSE_BODY}" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin).get("message", ""))' 2>/dev/null \
        || printf '%s' "${RESPONSE_BODY}"
}

# 断言接口返回码符合预期
expect() {
    local description="$1"
    local expected_code="$2"
    local method="$3"
    local path="$4"
    local body="${5:-}"

    request "${method}" "${path}" "${body}"

    if [ "${RESPONSE_CODE}" = "${expected_code}" ]; then
        PASS_COUNT=$((PASS_COUNT + 1))
        printf '  ✅ %-34s %s %s\n' "${description}" "${method}" "${path}"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        printf '  ❌ %-34s 期望 %s 实际 %s\n' "${description}" "${expected_code}" "${RESPONSE_CODE}"
        printf '     %s\n' "$(extract_message)"
    fi
}

# 等待服务启动
wait_for_server() {
    for _ in $(seq 1 40); do
        if curl -s -o /dev/null "${BASE_URL}/api/health"; then
            return 0
        fi
        sleep 0.25
    done
    printf '服务启动失败，日志内容：\n'
    cat "${SERVER_LOG}"
    exit 1
}

cd "${PROJECT_ROOT}" || exit 1
export FLASK_DEBUG=0
export PORT="${BASE_PORT}"
python3 app.py >"${SERVER_LOG}" 2>&1 &
SERVER_PID=$!
wait_for_server

printf '\n[1/4] 员工模块\n'
expect '健康检查'              200 GET  '/api/health'
expect '新增员工'              200 POST '/api/employees' \
    '{"name":"张三","department":"研发部","employee_no":"E1001","phone":"13800000000"}'
expect '工号重复'              400 POST '/api/employees' \
    '{"name":"李四","department":"研发部","employee_no":"E1001"}'
expect '员工列表'              200 GET  '/api/employees'
expect '员工详情'              200 GET  '/api/employees/1'
expect '不存在的员工'          404 GET  '/api/employees/999'

printf '\n[2/4] 打卡模块\n'
expect '上班签到'              200 POST '/api/checkins/in'  '{"employee_id":1}'
expect '重复签到'              400 POST '/api/checkins/in'  '{"employee_id":1}'
expect '查询打卡记录'          200 GET  '/api/checkins?employee_id=1'

printf '\n[3/4] 请假与加班模块\n'
expect '提交请假'              200 POST '/api/leaves' \
    '{"employee_id":1,"leave_type":"年假","start_date":"2026-11-05","end_date":"2026-11-06"}'
expect '请假类型非法'          400 POST '/api/leaves' \
    '{"employee_id":1,"leave_type":"婚假","start_date":"2026-11-05","end_date":"2026-11-06"}'
expect '开始日期晚于结束日期'  400 POST '/api/leaves' \
    '{"employee_id":1,"leave_type":"年假","start_date":"2026-11-08","end_date":"2026-11-06"}'
expect '审批通过请假'          200 POST '/api/leaves/1/approve' '{"approver":"王经理"}'
expect '重复审批请假'          400 POST '/api/leaves/1/approve' '{"approver":"王经理"}'
expect '请假日期冲突'          400 POST '/api/leaves' \
    '{"employee_id":1,"leave_type":"事假","start_date":"2026-11-05","end_date":"2026-11-07"}'
expect '提交加班'              200 POST '/api/overtimes' \
    '{"employee_id":1,"work_date":"2026-11-10","hours":3.5,"reason":"版本上线"}'
expect '加班时长为零'          400 POST '/api/overtimes' \
    '{"employee_id":1,"work_date":"2026-11-11","hours":0}'
expect '加班时长超限'          400 POST '/api/overtimes' \
    '{"employee_id":1,"work_date":"2026-11-11","hours":30}'
expect '同日重复加班'          400 POST '/api/overtimes' \
    '{"employee_id":1,"work_date":"2026-11-10","hours":2}'
expect '驳回加班'              200 POST '/api/overtimes/1/reject' '{"approver":"王经理"}'
expect '请假列表'              200 GET  '/api/leaves?status=approved'
expect '加班列表'              200 GET  '/api/overtimes'

printf '\n[4/4] 员工离职后的限制\n'
expect '员工离职'              200 DELETE '/api/employees/1'
expect '重复离职'              400 DELETE '/api/employees/1'
expect '离职后不能打卡'        400 POST '/api/checkins/out' '{"employee_id":1}'
expect '离职后不能请假'        400 POST '/api/leaves' \
    '{"employee_id":1,"leave_type":"事假","start_date":"2026-12-01","end_date":"2026-12-02"}'

printf '\n----------------------------------------\n'
printf '通过 %s 项，失败 %s 项\n' "${PASS_COUNT}" "${FAIL_COUNT}"
if [ "${FAIL_COUNT}" -gt 0 ]; then
    exit 1
fi
printf '接口冒烟测试全部通过\n'
