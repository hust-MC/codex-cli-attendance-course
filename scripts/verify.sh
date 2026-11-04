#!/usr/bin/env bash
# ============================================================
# verify.sh — 一键验收脚本
#
# 依次执行：静态检查 -> 单元测试 -> 接口冒烟 -> 页面可达性
# 任何一步失败立即退出，退出码非 0 表示验收未通过
#
# 用法：
#   bash scripts/verify.sh
#
# 退出码：0 全部通过，1 存在失败项
# ============================================================

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

FAIL_COUNT=0
STEP_COUNT=0

if command -v tput >/dev/null 2>&1 && [ -t 1 ]; then
    RED=$(tput setaf 1); GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4); BOLD=$(tput bold); RESET=$(tput sgr0)
else
    RED="[FAIL] "; GREEN="[PASS] "; YELLOW="[WARN] "; BLUE="[INFO] "; BOLD=""; RESET=""
fi

print_divider() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ----------------------------
# 记录一个检查项的结果
# ----------------------------
record() {
    local status="$1"
    local name="$2"
    STEP_COUNT=$((STEP_COUNT + 1))
    case "$status" in
        pass) echo "  ${GREEN}✅ 通过${RESET}  $name" ;;
        warn) echo "  ${YELLOW}⚠️  跳过${RESET}  $name" ;;
        fail) echo "  ${RED}❌ 失败${RESET}  $name"; FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    esac
    return 0
}

# ----------------------------
# 检查项 1：Python 语法编译
# ----------------------------
check_compile() {
    echo "  ${BOLD}[1/5] 语法编译${RESET}"
    if python3 -m compileall -q app.py db.py models services routes tests scripts > /dev/null 2>&1; then
        record pass "所有 Python 文件编译通过"
    else
        record fail "存在语法错误的文件"
        python3 -m compileall -q app.py db.py models services routes tests scripts 2>&1 | head -10
    fi
}

# ----------------------------
# 检查项 2：代码风格
# ----------------------------
check_style() {
    echo "  ${BOLD}[2/5] 代码风格${RESET}"

    # 行宽不超过 120 字符
    local long_files
    long_files=$(find app.py db.py models services routes tests scripts \
        -name "*.py" -exec awk 'length > 120 {print FILENAME":"FNR}' {} + 2>/dev/null)
    if [ -z "$long_files" ]; then
        record pass "所有代码行宽不超过 120 字符"
    else
        record fail "存在超长行"
        echo "$long_files" | head -5 | sed 's/^/         /'
    fi

    # 路由层不能出现 SQL
    local sql_in_routes
    sql_in_routes=$(grep -rn "SELECT \|INSERT \|UPDATE \|DELETE FROM" routes/ 2>/dev/null)
    if [ -z "$sql_in_routes" ]; then
        record pass "路由层没有直接写 SQL"
    else
        record fail "路由层出现了 SQL"
        echo "$sql_in_routes" | head -5 | sed 's/^/         /'
    fi

    # 调试输出不能留在代码里
    local debug_code
    debug_code=$(grep -rn "^\s*print(" app.py db.py models services routes 2>/dev/null)
    if [ -z "$debug_code" ]; then
        record pass "业务代码里没有遗留 print"
    else
        record fail "业务代码里有调试 print"
        echo "$debug_code" | head -5 | sed 's/^/         /'
    fi
}

# ----------------------------
# 检查项 3：单元测试
# ----------------------------
check_unit_tests() {
    echo "  ${BOLD}[3/5] 单元测试${RESET}"
    local output
    output=$(python3 -m unittest discover -s tests -v 2>&1)
    local exit_code=$?

    echo "$output" | grep -E "^Ran [0-9]+ test" | sed 's/^/         /'
    echo "$output" | grep -E "^(OK|FAILED)" | sed 's/^/         /'

    if [ $exit_code -eq 0 ]; then
        record pass "单元测试全部通过"
    else
        record fail "单元测试存在失败"
        echo "$output" | grep -E "^(FAIL|ERROR):" | head -10 | sed 's/^/         /'
    fi
}

# ----------------------------
# 检查项 4：接口冒烟
# ----------------------------
check_smoke() {
    echo "  ${BOLD}[4/5] 接口冒烟${RESET}"
    local output
    output=$(bash scripts/smoke-api.sh 2>&1)
    local exit_code=$?

    echo "$output" | grep -E "^通过 [0-9]+ 项" | sed 's/^/         /'

    if [ $exit_code -eq 0 ]; then
        record pass "接口冒烟全部通过"
    else
        record fail "接口冒烟存在失败"
        echo "$output" | grep -E "❌" | head -10 | sed 's/^/         /'
    fi
}

# ----------------------------
# 检查项 5：页面可达性
# ----------------------------
check_pages() {
    echo "  ${BOLD}[5/5] 页面可达性${RESET}"

    # 用临时端口和临时数据库启动服务，检查完立即关掉
    local port=3999
    local db_file
    db_file=$(mktemp -t verify_checkin_XXXXXX.db)

    CHECKIN_DB_PATH="$db_file" PORT=$port python3 app.py > /tmp/verify_app.log 2>&1 &
    local server_pid=$!

    # 等待服务起来
    local ready=0
    for _ in $(seq 1 20); do
        if curl -s -o /dev/null "http://127.0.0.1:$port/api/health" 2>/dev/null; then
            ready=1
            break
        fi
        sleep 0.5
    done

    if [ $ready -ne 1 ]; then
        record fail "服务在 10 秒内没有启动"
        kill "$server_pid" 2>/dev/null
        rm -f "$db_file"
        return 0
    fi

    local page_ok=1
    local pages=("/")

    # 静态资源路径从 templates/index.html 自动提取，避免前端改了目录还要改脚本
    local assets
    assets=$(grep -oE "url_for\('static', filename='[^']+'\)" templates/index.html \
        | sed "s/.*filename='\([^']*\)'.*/\1/" | sort -u)

    for asset in $assets; do
        pages+=("/static/$asset")
    done

    for page in "${pages[@]}"; do
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port$page")
        if [ "$code" != "200" ]; then
            page_ok=0
            echo "         $page 返回 HTTP $code"
        fi
    done

    if [ $page_ok -eq 1 ]; then
        record pass "首页和静态资源全部可达（共 ${#pages[@]} 个）"
    else
        record fail "存在无法访问的页面"
    fi

    kill "$server_pid" 2>/dev/null
    wait "$server_pid" 2>/dev/null
    rm -f "$db_file"
}

main() {
    print_divider
    echo "  ${BOLD}指尖打卡 2.0 · 一键验收${RESET}"
    echo "  项目目录：$PROJECT_DIR"
    print_divider
    echo ""

    check_compile
    echo ""
    check_style
    echo ""
    check_unit_tests
    echo ""
    check_smoke
    echo ""
    check_pages
    echo ""

    print_divider
    if [ "$FAIL_COUNT" -gt 0 ]; then
        echo "  ${RED}${BOLD}验收未通过：$FAIL_COUNT 项失败${RESET}"
        print_divider
        return 1
    fi
    echo "  ${GREEN}${BOLD}验收通过：全部检查项正常${RESET}"
    print_divider
    return 0
}

main "$@"
exit $?
