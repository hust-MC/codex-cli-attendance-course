#!/usr/bin/env bash
# ============================================================
# budget-check.sh — Codex Token 用量与预算守护
#
# 用法：
#   bash course/scripts/budget-check.sh              # 单次检查
#   bash course/scripts/budget-check.sh --by-model   # 按模型分组看用量
#   bash course/scripts/budget-check.sh --reset      # 清空累计记录
#
# 环境变量：
#   BUDGET_LIMIT    预算上限（人民币元），默认 10
#   WARN_THRESHOLD  警告阈值百分比，默认 80
#
# 退出码：0 未超预算，1 已超预算
#
# 数据来源：~/.codex/logs_2.sqlite
#   Codex 0.166 起不再写文本日志，token 用量记录在 logs 表的
#   feedback_log_body 字段里，形如：
#   ... post sampling token usage turn_id=xxx total_usage_tokens=42375
#   auto_compact_scope_limit=Some(244800)
#
# 修复记录：2026-11-04
#   原版靠 grep 文本日志统计 token，在 Codex 0.166 上永远读不到数据。
#   现在直接读 SQLite，并且按 thread 分组统计真实累计值。
# ============================================================

set -uo pipefail

BUDGET_LIMIT="${BUDGET_LIMIT:-10}"
WARN_THRESHOLD="${WARN_THRESHOLD:-80}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
LOG_DB="$CODEX_HOME/logs_2.sqlite"
USAGE_DB="$CODEX_HOME/budget.log"

# ----------------------------
# 颜色
# ----------------------------
if command -v tput >/dev/null 2>&1 && [ -t 1 ]; then
    RED=$(tput setaf 1); GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4); BOLD=$(tput bold); RESET=$(tput sgr0)
else
    RED="[FAIL] "; GREEN="[PASS] "; YELLOW="[WARN] "; BLUE="[INFO] "; BOLD=""; RESET=""
fi

print_divider() { echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }

# ----------------------------
# 统计每个线程的 token 用量
# Codex 的 total_usage_tokens 是该线程的累计值，所以取每个线程的最后一条
# ----------------------------
collect_usage() {
    python3 -c '
import re
import sqlite3
import sys

db_path = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "summary"

try:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
except sqlite3.Error:
    print("DB_ERROR")
    sys.exit(0)

token_re = re.compile(r"total_usage_tokens=(\d+)")
model_re = re.compile(r"model=([A-Za-z0-9._-]+)")
thread_re = re.compile(r"thread_id=([0-9a-f-]+)")
limit_re = re.compile(r"auto_compact_scope_limit=Some\((\d+)\)")

try:
    rows = conn.execute(
        "select id, feedback_log_body from logs "
        "where feedback_log_body like \"%total_usage_tokens=%\" order by id asc"
    ).fetchall()
except sqlite3.Error:
    print("DB_ERROR")
    sys.exit(0)

# 每个线程只保留最后一次上报的累计值
latest = {}
models = {}
limits = {}
for row_id, body in rows:
    token_match = token_re.search(body)
    if not token_match:
        continue
    tokens = int(token_match.group(1))
    thread_match = thread_re.search(body)
    thread_id = thread_match.group(1) if thread_match else "unknown"
    latest[thread_id] = tokens

    model_match = model_re.search(body)
    if model_match:
        models[thread_id] = model_match.group(1)

    limit_match = limit_re.search(body)
    if limit_match:
        limits[thread_id] = int(limit_match.group(1))

if mode == "by-model":
    by_model = {}
    for thread_id, tokens in latest.items():
        name = models.get(thread_id, "unknown")
        by_model[name] = by_model.get(name, 0) + tokens
    for name, tokens in sorted(by_model.items(), key=lambda item: -item[1]):
        print(f"{name}\t{tokens}")
    sys.exit(0)

if mode == "threads":
    for thread_id, tokens in sorted(latest.items(), key=lambda item: -item[1]):
        name = models.get(thread_id, "unknown")
        limit = limits.get(thread_id, 0)
        percent = (tokens / limit * 100) if limit else 0
        print(f"{thread_id}\t{name}\t{tokens}\t{limit}\t{percent:.1f}")
    sys.exit(0)

total = sum(latest.values())
max_limit = max(limits.values()) if limits else 0
threads = len(latest)
max_thread = max(latest.values()) if latest else 0
print(f"{total}\t{threads}\t{max_limit}\t{max_thread}")
' "$LOG_DB" "$1" 2>/dev/null
}

# ----------------------------
# 单次检查
# ----------------------------
check_once() {
    print_divider
    echo "  ${BOLD}Codex Token 预算检查${RESET}"
    print_divider

    if [ ! -f "$LOG_DB" ]; then
        echo "  ${YELLOW}找不到 $LOG_DB${RESET}"
        echo "  说明：Codex 0.166 起把日志放在 SQLite 里，这个文件在你跑过至少一次 codex 后才会出现。"
        return 0
    fi

    local summary
    summary=$(collect_usage summary)
    if [ "$summary" = "DB_ERROR" ]; then
        echo "  ${RED}无法读取 $LOG_DB${RESET}"
        return 1
    fi

    local total_tokens
    local thread_count
    local context_limit
    local max_thread_tokens
    total_tokens=$(printf '%s' "$summary" | cut -f1)
    thread_count=$(printf '%s' "$summary" | cut -f2)
    context_limit=$(printf '%s' "$summary" | cut -f3)
    max_thread_tokens=$(printf '%s' "$summary" | cut -f4)

    echo "  会话线程数：$thread_count"
    echo "  累计 Token：$total_tokens"
    if [ "$context_limit" -gt 0 ] 2>/dev/null; then
        echo "  单会话上下文上限：$context_limit"
        if [ "$max_thread_tokens" -gt 0 ] 2>/dev/null; then
            local percent
            percent=$(awk "BEGIN {printf \"%.1f\", $max_thread_tokens / $context_limit * 100}")
            echo "  最长会话占用：${percent}%（$max_thread_tokens / $context_limit）"
        fi
    fi
    echo ""

    # ----------------------------
    # 上下文爆炸预警：这是 2.5 节第二招的核心证据
    # ----------------------------
    echo "  ${BOLD}上下文占用最高的会话${RESET}"
    local thread_rows
    thread_rows=$(collect_usage threads)
    if [ -n "$thread_rows" ]; then
        printf '%s\n' "$thread_rows" | head -5 | while IFS=$'\t' read -r tid name tokens limit percent; do
            [ -z "$tid" ] && continue
            local short="${tid:0:8}"
            printf '    %s  %-18s %8s tokens  %5s%%\n' "$short" "$name" "$tokens" "$percent"
        done
    fi
    echo ""

    # ----------------------------
    # 按模型统计：这是 2.5 节第一招的证据
    # ----------------------------
    echo "  ${BOLD}按模型统计${RESET}"
    local model_rows
    model_rows=$(collect_usage by-model)
    if [ -n "$model_rows" ]; then
        # 注意：printf 不带换行时，read 会丢弃最后一行，这里必须补上换行符
        printf '%s\n' "$model_rows" | while IFS=$'\t' read -r name tokens; do
            [ -z "$name" ] && continue
            printf '    %-18s %8s tokens\n' "$name" "$tokens"
        done
    fi
    echo ""

    # ----------------------------
    # 预算判断
    # ----------------------------
    # 单价可通过环境变量覆盖，单位是 元 / 千 Token
    # 默认按 DeepSeek 混合调用估算：输入约 0.5 元/百万，输出约 2 元/百万，
    # 按输入输出 7:3 加权后取 1.1 元/百万，也就是 0.0011 元/千 Token。
    # 演示时可改成 COST_PER_1K=0.01 让人直观看到超支效果。
    local cost_per_1k="${COST_PER_1K:-0.0011}"
    local cost
    cost=$(awk "BEGIN {printf \"%.4f\", $total_tokens / 1000 * $cost_per_1k}")
    echo "  ${BOLD}按 ${cost_per_1k} 元/千 Token 估算${RESET}：${cost} 元（预算上限 ${BUDGET_LIMIT} 元）"

    local used_percent
    used_percent=$(awk "BEGIN {printf \"%.1f\", $cost / $BUDGET_LIMIT * 100}")

    if awk "BEGIN {exit !($cost > $BUDGET_LIMIT)}"; then
        echo "  ${RED}${BOLD}已超预算${RESET}（用了 ${used_percent}%）"
        echo ""
        echo "  建议立刻执行："
        echo "    1. /compact      压缩当前会话上下文"
        echo "    2. /clear        清空上下文重新开始"
        echo "    3. 换更便宜的模型继续干剩余任务"
        return 1
    elif awk "BEGIN {exit !($used_percent >= $WARN_THRESHOLD)}"; then
        echo "  ${YELLOW}${BOLD}接近预算${RESET}（用了 ${used_percent}%，阈值 ${WARN_THRESHOLD}%）"
        echo "  建议：先 /compact，再继续。"
        return 0
    else
        echo "  ${GREEN}${BOLD}预算充足${RESET}（用了 ${used_percent}%）"
        return 0
    fi
}

# ----------------------------
# 清空累计记录
# ----------------------------
reset_usage() {
    if [ -f "$USAGE_DB" ]; then
        local before
        before=$(wc -l < "$USAGE_DB" | tr -d ' ')
        mv "$USAGE_DB" "$USAGE_DB.bak"
        echo "  已重置预算记录（原 $before 行备份到 $USAGE_DB.bak）"
        echo "  ${YELLOW}注意：Codex 自身的 logs_2.sqlite 不受影响，历史 token 统计依然保留。${RESET}"
    else
        echo "  没有找到预算记录文件，无需重置。"
    fi
    return 0
}

case "${1:-}" in
    --reset)
        reset_usage
        ;;
    --by-model)
        collect_usage by-model | while IFS=$'\t' read -r name tokens; do
            [ -z "$name" ] && continue
            printf '    %-18s %8s tokens\n' "$name" "$tokens"
        done
        ;;
    --threads)
        collect_usage threads | while IFS=$'\t' read -r tid name tokens limit percent; do
            [ -z "$tid" ] && continue
            printf '    %-8s %-18s %8s tokens  %5s%%\n' "${tid:0:8}" "$name" "$tokens" "$percent"
        done
        ;;
    *)
        check_once
        exit $?
        ;;
esac
