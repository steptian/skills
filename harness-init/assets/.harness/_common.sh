#!/bin/bash
# ============================================================================
# 公共模块 - 被其他脚本 source 引入，不直接执行
# 提供：颜色定义、Claude 配置、进程清理、信号捕获、统一执行函数
# ============================================================================

# 防止重复加载
[ -n "$_COMMON_LOADED" ] && return 0
_COMMON_LOADED=1

# ============================================================================
# 颜色定义
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# Claude Code 配置
# ============================================================================
CLAUDE_CMD=${CLAUDE_CMD:-"claude"}
CLAUDE_ARGS=${CLAUDE_ARGS:-"--dangerously-skip-permissions"}

# ============================================================================
# 进程管理与资源清理
# ============================================================================
_CLEANUP_DONE=0

# 递归终止进程树（先终止子进程，再终止父进程）
kill_tree() {
    local pid=$1
    local sig=${2:-TERM}

    local children
    children=$(pgrep -P "$pid" 2>/dev/null) || true

    for child in $children; do
        kill_tree "$child" "$sig"
    done

    kill -"$sig" "$pid" 2>/dev/null || true
}

# 核心清理函数：终止所有子进程并恢复终端
_do_cleanup() {
    [ "$_CLEANUP_DONE" = "1" ] && return 0
    _CLEANUP_DONE=1

    stty sane 2>/dev/null || true

    echo ""
    echo -e "${YELLOW}[Cleanup] 正在清理资源...${NC}"

    local children
    children=$(pgrep -P $$ 2>/dev/null) || true

    if [ -n "$children" ]; then
        for child in $children; do
            kill_tree "$child" "TERM"
        done

        sleep 1

        children=$(pgrep -P $$ 2>/dev/null) || true
        for child in $children; do
            kill_tree "$child" "KILL"
        done
    fi

    wait 2>/dev/null || true

    echo -e "${GREEN}[Cleanup] 资源清理完成${NC}"
}

# 注册信号处理（在主脚本的 main 函数开头调用）
setup_cleanup() {
    trap _do_cleanup EXIT
    trap 'echo ""; echo -e "${YELLOW}收到中断信号 (Ctrl+C)${NC}"; exit 130' INT
    trap 'echo ""; echo -e "${YELLOW}收到终止信号${NC}"; exit 143' TERM
}

# ============================================================================
# Claude Code 统一执行
# ============================================================================

# 检查 Claude Code 是否可用
check_claude() {
    if ! command -v "$CLAUDE_CMD" &> /dev/null; then
        echo -e "${RED}错误: 找不到 Claude Code 命令 '$CLAUDE_CMD'${NC}"
        echo "请确保 Claude Code 已安装并配置好"
        exit 1
    fi
}

# 运行 Claude Code（自动处理实时输出与日志）
#
# 用法: run_claude <mode> <prompt> [log_file]
#   mode     : "interactive"  — 交互式 TUI 模式
#              "print"        — 非交互式纯文本模式 (--print)
#   prompt   : 发送给 Claude 的提示文本
#   log_file : 可选，日志文件路径；提供时同时保存日志
#
# 行为矩阵:
#   interactive + log_file  → script -q 保持 TUI 的同时写日志
#   interactive 无 log_file → 直接运行 TUI
#   print + log_file        → --print | tee 实时终端输出 + 日志
#   print 无 log_file       → --print 直接输出到终端
run_claude() {
    local mode="$1"
    local prompt="$2"
    local log_file="${3:-}"

    if [ "$mode" = "interactive" ]; then
        if [ -n "$log_file" ]; then
            echo -e "${BLUE}模式: 交互式 (实时输出 + 日志)${NC}"
            echo "日志: $log_file"
            echo ""
            script -q "$log_file" $CLAUDE_CMD $CLAUDE_ARGS "$prompt"
        else
            echo -e "${BLUE}模式: 交互式 (实时输出)${NC}"
            echo ""
            $CLAUDE_CMD $CLAUDE_ARGS "$prompt"
        fi
    else
        if [ -n "$log_file" ]; then
            echo -e "${BLUE}模式: 非交互式 (实时输出 + 日志)${NC}"
            echo "日志: $log_file"
            echo ""
            # 使用 Python 实现无缓冲 tee，兼容 macOS/Linux
            # 传日志路径通过命令行参数避免环境变量问题
            ( set -o pipefail; $CLAUDE_CMD $CLAUDE_ARGS --print "$prompt" 2>&1 | python3 -u -c "
import sys
log_path = sys.argv[1]
log_file = open(log_path, 'wb')
try:
    for line in sys.stdin.buffer:
        sys.stdout.buffer.write(line)
        sys.stdout.buffer.flush()
        log_file.write(line)
        log_file.flush()
finally:
    log_file.close()
" - "$log_file" )
        else
            echo -e "${BLUE}模式: 非交互式 (实时输出)${NC}"
            echo ""
            $CLAUDE_CMD $CLAUDE_ARGS --print "$prompt"
        fi
    fi

    stty sane 2>/dev/null || true
}
