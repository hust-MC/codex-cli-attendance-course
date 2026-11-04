#!/usr/bin/env bash
# ============================================================
# codex-doctor.sh — Codex 环境自诊脚本
# 用途：检查 Codex 安装环境的 8 项关键问题，一键定位
#
# 用法：
#   bash course/scripts/codex-doctor.sh
#
# 退出码：全部通过为 0，有失败项为 1
#
# 修复记录：2026-11-04
#   原版在 check_item 函数末尾用 `[ -n "$fix" ] && echo ...`，
#   当 fix 为空时该行返回 1，配合 set -e 会让脚本在第一项检查后静默退出。
#   现在改成 if 判断，并且所有检查项统一返回 0。
# ============================================================

set -uo pipefail

# ----------------------------
# 颜色定义（兼容非交互终端）
# ----------------------------
if command -v tput >/dev/null 2>&1 && [ -t 1 ]; then
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    BOLD=$(tput bold)
    RESET=$(tput sgr0)
else
    RED="[FAIL] "
    GREEN="[PASS] "
    YELLOW="[WARN] "
    BLUE="[INFO] "
    BOLD=""
    RESET=""
fi

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

print_divider() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

print_header() {
    echo ""
    print_divider
    echo "  ${BOLD}Codex 环境自诊  ·  检查 8 项关键配置${RESET}"
    print_divider
}

# ----------------------------
# 打印单项检查结果
# 注意：函数最后必须显式 return 0，否则 set -e 会把空判断当成失败
# ----------------------------
check_item() {
    local name="$1"
    local status="$2"
    local detail="$3"
    local fix="${4:-}"

    case "$status" in
        pass) PASS_COUNT=$((PASS_COUNT + 1)); echo "  ${GREEN}✅ 通过${RESET}  $name" ;;
        warn) WARN_COUNT=$((WARN_COUNT + 1)); echo "  ${YELLOW}⚠️  风险${RESET}  $name" ;;
        fail) FAIL_COUNT=$((FAIL_COUNT + 1)); echo "  ${RED}❌ 失败${RESET}  $name" ;;
    esac

    if [ -n "$detail" ]; then
        echo "         现状：$detail"
    fi
    if [ -n "$fix" ]; then
        echo "         解药：$fix"
    fi
    return 0
}

detect_os() {
    case "$(uname -s)" in
        Darwin) echo "macOS" ;;
        Linux) echo "Linux" ;;
        MINGW*|MSYS*|CYGWIN*) echo "Windows" ;;
        *) echo "Unknown" ;;
    esac
}

# ----------------------------
# 检查项 1：Node.js 版本
# ----------------------------
check_node_version() {
    local node_version
    node_version=$(node -v 2>/dev/null || echo "NOT_FOUND")

    if [ "$node_version" = "NOT_FOUND" ]; then
        check_item "Node.js 版本" "fail" "未找到 node 命令" \
            "安装 Node.js 18+：https://nodejs.org 或用 nvm"
        return 0
    fi

    local major="${node_version#v}"
    major="${major%%.*}"

    if [ "$major" -ge 18 ]; then
        check_item "Node.js 版本" "pass" "$node_version (满足要求 ≥v18)"
    else
        check_item "Node.js 版本" "fail" "$node_version (需要 ≥v18)" \
            "运行：nvm install 20 && nvm use 20"
    fi
    return 0
}

# ----------------------------
# 检查项 2：npm 可用性
# ----------------------------
check_npm() {
    local npm_version
    npm_version=$(npm -v 2>/dev/null || echo "NOT_FOUND")

    if [ "$npm_version" = "NOT_FOUND" ]; then
        check_item "npm 包管理器" "fail" "未找到 npm 命令" "重新安装 Node.js（自带 npm）"
    else
        check_item "npm 包管理器" "pass" "npm v$npm_version"
    fi
    return 0
}

# ----------------------------
# 检查项 3：npm 全局目录权限
# 这是 EACCES 报错的根源，第四章和第二章 2.2 节都会讲
# ----------------------------
check_npm_permission() {
    local npm_global_path
    npm_global_path=$(npm config get prefix 2>/dev/null)

    if [ -z "$npm_global_path" ]; then
        check_item "npm 全局目录权限" "warn" "无法获取 npm prefix" ""
        return 0
    fi

    if [ -w "$npm_global_path" ] 2>/dev/null; then
        check_item "npm 全局目录权限" "pass" "$npm_global_path (可写)"
    else
        check_item "npm 全局目录权限" "fail" "$npm_global_path (无写权限)" \
            "根治：npm config set prefix ~/.npm-global && echo 'export PATH=~/.npm-global/bin:\$PATH' >> ~/.zshrc"
    fi
    return 0
}

# ----------------------------
# 检查项 4：Codex CLI 安装状态
# ----------------------------
check_codex_installed() {
    local codex_version
    codex_version=$(codex --version 2>/dev/null || echo "NOT_FOUND")

    if [ "$codex_version" = "NOT_FOUND" ]; then
        check_item "Codex CLI 安装状态" "fail" "codex 命令未找到" "运行：npm install -g @openai/codex"
    else
        check_item "Codex CLI 安装状态" "pass" "$codex_version"
    fi
    return 0
}

# ----------------------------
# 检查项 5：Codex 实际使用的路径
# npm 全局装在 root 目录下时，普通用户更新会报 EACCES
# ----------------------------
check_codex_path() {
    local codex_path
    codex_path=$(which codex 2>/dev/null || echo "NOT_FOUND")

    if [ "$codex_path" = "NOT_FOUND" ]; then
        check_item "Codex 实际路径" "warn" "未找到 codex 可执行文件" ""
        return 0
    fi

    if [[ "$codex_path" == *"/.npm-global/"* ]]; then
        check_item "Codex 实际路径" "pass" "$codex_path (用户目录，可自行更新)"
    elif [[ "$codex_path" == "/usr/local/"* ]] || [[ "$codex_path" == "/usr/"* ]]; then
        check_item "Codex 实际路径" "fail" "$codex_path (系统目录，归 root，更新会报 EACCES)" \
            "根治：npm config set prefix ~/.npm-global && npm install -g @openai/codex"
    else
        check_item "Codex 实际路径" "pass" "$codex_path"
    fi
    return 0
}

# ----------------------------
# 读取 config.toml 里的顶层键
# 用 Python 解析，避免 sed 把 model 和 model_provider 混淆
# ----------------------------
read_config_key() {
    local config_path="$1"
    local key="$2"

    python3 -c '
import sys

path, key = sys.argv[1], sys.argv[2]
try:
    content = open(path, encoding="utf-8").read()
except OSError:
    sys.exit(0)

for line in content.splitlines():
    if line.startswith("[") or "=" not in line:
        continue
    name, _, raw = line.partition("=")
    if name.strip() == key:
        value = raw.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"'"'"):
            value = value[1:-1]
        print(value)
        break
' "$config_path" "$key" 2>/dev/null
}

# ----------------------------
# 检查项 6：模型与接口配置
# Codex 0.166 起模型信息在 ~/.codex/config.toml 里
# ----------------------------
check_model_config() {
    local config_path="$HOME/.codex/config.toml"

    if [ ! -f "$config_path" ]; then
        check_item "模型与接口配置" "fail" "$config_path 不存在" "运行：codex login 或手动创建 config.toml"
        return 0
    fi

    local model=""
    local provider=""
    model=$(read_config_key "$config_path" "model")
    provider=$(read_config_key "$config_path" "model_provider")

    if [ -n "$model" ]; then
        check_item "模型与接口配置" "pass" "model=$model provider=${provider:-默认}"
    else
        check_item "模型与接口配置" "warn" "$config_path 里没有配置 model，使用默认模型" \
            "在 config.toml 里加上：model = \"你的模型名\""
    fi
    return 0
}

# ----------------------------
# 检查项 7：登录状态
# ----------------------------
check_login() {
    local auth_path="$HOME/.codex/auth.json"

    if [ ! -f "$auth_path" ]; then
        check_item "登录状态" "fail" "没有找到 $auth_path" "运行：codex login"
        return 0
    fi

    if [ -s "$auth_path" ]; then
        check_item "登录状态" "pass" "已配置凭据 ($auth_path)"
    else
        check_item "登录状态" "fail" "$auth_path 是空文件" "运行：codex login"
    fi
    return 0
}

# ----------------------------
# 检查项 8：接口连通性
# 直接探测配置里的 base_url，避免依赖环境变量名
# ----------------------------
check_network() {
    local base_url=""

    if [ -f "$HOME/.codex/config.toml" ]; then
        base_url=$(read_config_key "$HOME/.codex/config.toml" "base_url")
    fi

    if [ -z "$base_url" ]; then
        base_url="${OPENAI_API_BASE:-https://api.openai.com}"
    fi

    echo -n "  ${BLUE}⏳${RESET}  接口连通性  "

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        -H "Authorization: Bearer ${OPENAI_API_KEY:-probe}" \
        "${base_url%/}/models" 2>/dev/null)
    # curl 失败时返回空串，这里统一补成 000，避免和 -w 的输出拼成 000000
    if [ -z "$http_code" ]; then
        http_code="000"
    fi

    case "$http_code" in
        200|401|403)
            echo "${GREEN}✅ 可达${RESET}  HTTP $http_code ($base_url)"
            ;;
        429)
            echo "${YELLOW}⚠️  风险${RESET}  HTTP 429 (触发限速，网络是通的)"
            ;;
        000)
            echo "${RED}❌ 失败${RESET}  连接超时或域名解析失败"
            check_item "接口连通性" "fail" "无法访问 $base_url" "检查网络或代理配置"
            ;;
        *)
            echo "${RED}❌ 失败${RESET}  HTTP $http_code"
            check_item "接口连通性" "fail" "HTTP $http_code" ""
            ;;
    esac
    return 0
}

# ----------------------------
# 汇总
# ----------------------------
print_summary() {
    echo ""
    print_divider

    if [ "$FAIL_COUNT" -gt 0 ]; then
        echo "  ${RED}${BOLD}发现 $FAIL_COUNT 项失败${RESET}"
    elif [ "$WARN_COUNT" -gt 0 ]; then
        echo "  ${YELLOW}${BOLD}全部通过，但有 $WARN_COUNT 项风险${RESET}"
    else
        echo "  ${GREEN}${BOLD}8 项检查全部通过，环境健康${RESET}"
    fi

    echo "  通过 $PASS_COUNT 项，风险 $WARN_COUNT 项，失败 $FAIL_COUNT 项"
    echo ""
    return 0
}

main() {
    print_header
    echo "  系统：$(detect_os)  |  Node: $(node -v 2>/dev/null || echo '未安装')"
    echo ""

    check_node_version
    check_npm
    check_npm_permission
    check_codex_installed
    check_codex_path
    check_model_config
    check_login
    check_network

    print_summary

    if [ "$FAIL_COUNT" -gt 0 ]; then
        return 1
    fi
    return 0
}

main "$@"
