#!/bin/bash
# ============================================================================
# Long-Running Agent 统一入口
#
# 用法:
#   ./dev.sh plan                       从需求文档生成功能清单
#   ./dev.sh migrate                    从现有代码库迁移
#   ./dev.sh run  [--auto] [-n 20]      自动循环开发
#   ./dev.sh status                     查看当前进度
#   ./dev.sh env                        初始化开发环境
# ============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HARNESS_DIR="$PROJECT_ROOT/.harness"
FEATURE_CLI="$HARNESS_DIR/feature_cli.py"
CONFIG_FILE="$HARNESS_DIR/config.json"

source "$HARNESS_DIR/_common.sh"

# ============================================================================
# 版本检查（静默，仅在过期时提示）
# ============================================================================
check_harness_version() {
    local source_version_file="$HOME/.claude/skills/harness-init/assets/.harness/VERSION"
    local current_version_file="$HARNESS_DIR/VERSION"

    [ ! -f "$source_version_file" ] && return 0
    [ ! -f "$current_version_file" ] && return 0

    local current latest
    current=$(tr -d '[:space:]' < "$current_version_file")
    latest=$(tr -d '[:space:]' < "$source_version_file")
    [ "$current" = "$latest" ] && return 0

    # 语义化版本比较
    local need_update
    need_update=$(python3 -c "
def pv(v):
    return [int(''.join(c for c in p if c.isdigit()) or '0') for p in v.split('.')]
c = pv('$current'.split('-')[0])
l = pv('$latest'.split('-')[0])
for i in range(max(len(c), len(l))):
    a = c[i] if i < len(c) else 0
    b = l[i] if i < len(l) else 0
    if b > a:
        print('1')
        break
    elif b < a:
        break
" 2>/dev/null)

    if [ "$need_update" = "1" ]; then
        echo -e "${YELLOW}⚠ Harness 有新版本: $current → $latest${NC}"
        echo -e "${YELLOW}  运行 '/harness-init 更新' 或 update.sh 升级${NC}"
        echo ""
    fi
}

# 读取配置文件
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        # 使用 Python 解析 JSON 配置（只处理顶层简单值）
        eval $(python3 -c "
import json
with open('$CONFIG_FILE') as f:
    cfg = json.load(f)
for k, v in cfg.items():
    if isinstance(v, bool):
        print(f'{k}={str(v).lower()}')
    elif isinstance(v, str):
        print(f'{k}=\"{v}\"')
    elif isinstance(v, (int, float)):
        print(f'{k}={v}')
    # 跳过嵌套对象（如 iteration）
" 2>/dev/null)
    fi
}

# 默认配置
MAX_SESSIONS=${MAX_SESSIONS:-10}
AUTO_CONFIRM=${AUTO_CONFIRM:-0}
INTERACTIVE=${INTERACTIVE:-1}
STALE_HOURS=${STALE_HOURS:-24}
CLAUDE_ARGS=${CLAUDE_ARGS:-"--dangerously-skip-permissions"}

# 加载用户配置（覆盖默认值）
load_config

LOG_DIR="$HARNESS_DIR/logs"
mkdir -p "$LOG_DIR"

# ============================================================================
# add — 添加迭代需求到功能清单
# ============================================================================
cmd_add() {
    local doc_path="${1:-}"
    local force_flag=""
    local type_flag=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force|-f)  force_flag="--force"; shift ;;
            --type|-t)   type_flag="--type $2"; shift 2 ;;
            -h|--help)   echo "用法: dev.sh add <文档路径> [--type bugfix|feature|enhancement] [--force]"; return 0 ;;
            *)           doc_path="$1"; shift ;;
        esac
    done

    if [ -z "$doc_path" ]; then
        echo -e "${RED}错误: 请指定需求文档路径${NC}"
        echo "用法: dev.sh add <文档路径> [--type bugfix|feature|enhancement] [--force]"
        return 1
    fi

    if [ ! -f "$doc_path" ]; then
        echo -e "${RED}错误: 文件不存在: $doc_path${NC}"
        return 1
    fi

    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     Harness · 添加迭代需求                 ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""

    # 调用 feature_cli.py 添加
    python3 "$FEATURE_CLI" add "$doc_path" $type_flag $force_flag

    echo ""
    echo -e "${CYAN}下一步: .harness/dev.sh run${NC}"
}

# ============================================================================
# remember — 记录设计决策
# ============================================================================
cmd_remember() {
    local topic="${1:-}"
    local reason="${2:-}"

    if [ -z "$topic" ]; then
        echo -e "${RED}错误: 请提供决策主题${NC}"
        echo "用法: dev.sh remember <决策主题> <决策原因>"
        echo "示例: dev.sh remember \"认证方案选择 JWT\" \"前后端分离架构，JWT 更适合跨域场景\""
        return 1
    fi

    if [ -z "$reason" ]; then
        echo -e "${YELLOW}提示: 未提供决策原因${NC}"
        reason="(未记录原因)"
    fi

    python3 "$FEATURE_CLI" remember "$topic" "$reason"
}

# ============================================================================
# doctor — 项目健康检查
# ============================================================================
cmd_doctor() {
    python3 "$FEATURE_CLI" doctor
}

# ============================================================================
# lint — 代码规范检查
# ============================================================================
cmd_lint() {
    local lint_script="$HARNESS_DIR/scripts/linter.py"
    local fix_flag=""
    local json_flag=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fix)   fix_flag="--fix"; shift ;;
            --json)  json_flag="--json"; shift ;;
            -h|--help)
                echo "Harness · 代码规范检查"
                echo ""
                echo "用法: dev.sh lint [路径] [--fix] [--json]"
                echo ""
                echo "选项:"
                echo "  --fix    自动修复可修复的问题"
                echo "  --json   JSON 格式输出"
                echo ""
                echo "检查项:"
                echo "  - 文件大小 (≤300 行)"
                echo "  - 函数长度 (≤50 行)"
                echo "  - 禁止模式 (空 except、SELECT *、硬编码密钥)"
                echo "  - 架构约束 (分层调用)"
                return 0
                ;;
            *)       shift ;;
        esac
    done

    if [ ! -f "$lint_script" ]; then
        echo -e "${RED}错误: linter.py 不存在${NC}"
        echo "请运行 .harness/dev.sh update 更新框架"
        return 1
    fi

    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     Harness · 代码规范检查                ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""

    python3 "$lint_script" . $fix_flag $json_flag
}

# ============================================================================
# garden — 技术债管理
# ============================================================================
cmd_garden() {
    local garden_script="$HARNESS_DIR/scripts/garden.py"
    local auto_flag=""
    local todos_flag=""
    local json_flag=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto)        auto_flag="--auto"; shift ;;
            --create-todos) todos_flag="--create-todos"; shift ;;
            --json)        json_flag="--json"; shift ;;
            -h|--help)
                echo "Harness · 技术债花园"
                echo ""
                echo "用法: dev.sh garden [--auto] [--create-todos] [--json]"
                echo ""
                echo "选项:"
                echo "  --auto          自动修复简单问题"
                echo "  --create-todos  为复杂问题创建待办"
                echo "  --json          JSON 格式输出"
                echo ""
                echo "功能:"
                echo "  - 扫描代码规范违规"
                echo "  - 检查文档一致性"
                echo "  - 扫描 TODO/FIXME 标记"
                echo "  - 自动修复格式问题"
                return 0
                ;;
            *)             shift ;;
        esac
    done

    if [ ! -f "$garden_script" ]; then
        echo -e "${RED}错误: garden.py 不存在${NC}"
        echo "请运行 .harness/dev.sh update 更新框架"
        return 1
    fi

    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     Harness · 技术债花园                  ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""

    python3 "$garden_script" $auto_flag $todos_flag $json_flag
}

# ============================================================================
# impact — 代码变更影响范围分析
# ============================================================================
cmd_impact() {
    local impact_script="$HARNESS_DIR/scripts/impact_analyzer.py"
    local staged_flag=""
    local commit_ref=""
    local json_flag=""
    local tests_flag=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --staged)  staged_flag="--staged"; shift ;;
            --commit)  commit_ref="--commit $2"; shift 2 ;;
            --json)    json_flag="--json"; shift ;;
            --tests)   tests_flag="--suggest-tests"; shift ;;
            -h|--help)
                echo "Harness · 代码变更影响范围分析"
                echo ""
                echo "用法: dev.sh impact [选项]"
                echo ""
                echo "选项:"
                echo "  --staged         分析已暂存变更"
                echo "  --commit <ref>   分析指定提交的变更"
                echo "  --json           JSON 格式输出"
                echo "  --tests          仅输出测试建议"
                echo ""
                echo "功能:"
                echo "  - 检测 Git 变更 (staged/unstaged/committed)"
                echo "  - 分析文件依赖关系 (import/call graph)"
                echo "  - 识别受影响的测试文件"
                echo "  - 生成测试覆盖建议"
                echo "  - 评估风险等级"
                return 0
                ;;
            *)       shift ;;
        esac
    done

    if [ ! -f "$impact_script" ]; then
        echo -e "${RED}错误: impact_analyzer.py 不存在${NC}"
        echo "请运行 .harness/dev.sh update 更新框架"
        return 1
    fi

    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     Harness · 影响范围分析                ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""

    python3 "$impact_script" $staged_flag $commit_ref $json_flag $tests_flag
}

# ============================================================================
# memory — 记忆系统管理
# ============================================================================
cmd_memory() {
    local subcmd="${1:-status}"

    case $subcmd in
        status|show|add|search|export)
            shift
            python3 "$FEATURE_CLI" memory "$subcmd" "$@"
            ;;
        -h|--help)
            echo "Harness · 记忆系统"
            echo ""
            echo "用法: dev.sh memory <command> [args]"
            echo ""
            echo "命令:"
            echo "  status              显示记忆系统状态"
            echo "  show <type>         显示指定类型的记忆"
            echo "  add <type> <content> 添加记忆条目"
            echo "  search <query>      搜索记忆内容"
            echo "  export              导出记忆为可注入格式"
            echo ""
            echo "记忆类型: project, decisions, structure, interfaces, history"
            ;;
        *)
            echo -e "${RED}错误: 未知的记忆命令 '$subcmd'${NC}"
            echo "可用命令: status, show, add, search, export"
            return 1
            ;;
    esac
}

# ============================================================================
# plan — 从 requirements.md 生成 features.json
# ============================================================================
cmd_plan() {
    setup_cleanup

    local req_file="$HARNESS_DIR/requirements.md"
    if [ ! -f "$req_file" ]; then
        echo -e "${RED}错误: 找不到 $req_file${NC}"
        exit 1
    fi
    if ! grep -q "[^[:space:]]" "$req_file"; then
        echo -e "${YELLOW}需求文档为空，请先编辑 $req_file${NC}"
        exit 1
    fi

    check_claude

    echo -e "${BLUE}[Plan] 启动 Initializer Agent ...${NC}"
    echo "正在分析需求并生成功能清单"
    echo ""

    cd "$PROJECT_ROOT"
    local prompt
    prompt="$(cat "$HARNESS_DIR/prompts/initializer.txt")"
    local log="$LOG_DIR/plan_$(date +%Y%m%d_%H%M%S).log"

    run_claude "print" "$prompt" "$log"

    echo ""
    if [ -f "$HARNESS_DIR/features.json" ] || [ -f "$HARNESS_DIR/feature_list.json" ]; then
        echo -e "${GREEN}✅ 功能清单已生成${NC}"
        python3 "$FEATURE_CLI" status
        echo ""
        echo -e "${CYAN}下一步: .harness/dev.sh run${NC}"
    else
        echo -e "${RED}❌ 功能清单未生成，请检查输出${NC}"
    fi
}

# ============================================================================
# migrate — 从现有代码库迁移
# ============================================================================
cmd_migrate() {
    setup_cleanup
    check_claude

    cd "$PROJECT_ROOT"

    echo -e "${BLUE}[Migrate] 分析现有项目...${NC}"
    echo ""
    echo "文件结构预览:"
    find . -maxdepth 3 -type f \
        \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" \
           -o -name "*.go" -o -name "*.java" -o -name "*.rs" \) \
        ! -path "*/node_modules/*" ! -path "*/venv/*" ! -path "*/.git/*" \
        2>/dev/null | head -30
    echo ""

    echo -e "${BLUE}[Migrate] 启动 Migration Agent...${NC}"
    echo ""

    local prompt
    prompt="$(cat "$HARNESS_DIR/prompts/migration.txt")"
    local log="$LOG_DIR/migrate_$(date +%Y%m%d_%H%M%S).log"

    if [ "$INTERACTIVE" = "1" ]; then
        run_claude "interactive" "$prompt" "$log"
    else
        run_claude "print" "$prompt" "$log"
    fi

    echo ""
    if [ -f "$HARNESS_DIR/features.json" ] || [ -f "$HARNESS_DIR/feature_list.json" ]; then
        echo -e "${GREEN}✅ 迁移完成${NC}"
        python3 "$FEATURE_CLI" status
        echo ""
        echo -e "${CYAN}下一步: .harness/dev.sh run${NC}"
    else
        echo -e "${RED}❌ 迁移失败，请检查输出${NC}"
    fi
}

# ============================================================================
# run — 自动循环开发
# ============================================================================
cmd_run() {
    local max_sessions=${MAX_SESSIONS:-10}
    local auto_confirm=${AUTO_CONFIRM:-0}
    local interactive=${INTERACTIVE:-1}  # 默认跟随配置文件

    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto)  auto_confirm=1; shift ;;
            --print) interactive=0; shift ;;  # 命令行覆盖：非交互模式
            -n)      max_sessions="$2"; shift 2 ;;
            *)       echo "未知参数: $1"; exit 1 ;;
        esac
    done

    setup_cleanup
    check_claude

    cd "$PROJECT_ROOT"

    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     Long-Running Agent · 自动循环开发     ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  最大会话: $max_sessions | 自动确认: $([ "$auto_confirm" = "1" ] && echo "是" || echo "否") | 模式: $([ "$interactive" = "1" ] && echo "交互" || echo "非交互")"
    echo ""

    local session_count=0
    local pending
    pending=$(python3 "$FEATURE_CLI" pending-count)

    if [ "$pending" -eq 0 ]; then
        echo -e "${YELLOW}没有待完成的功能${NC}"
        exit 0
    fi

    while [ "$pending" -gt 0 ] && [ "$session_count" -lt "$max_sessions" ]; do
        session_count=$((session_count + 1))

        local next_feature
        next_feature=$(python3 "$FEATURE_CLI" next 2>/dev/null || true)
        if [ -z "$next_feature" ]; then
            echo -e "${YELLOW}没有可选的功能（依赖未满足或全部完成）${NC}"
            break
        fi

        echo ""
        echo -e "${CYAN}── 会话 #$session_count ─────────────────────────────${NC}"
        echo "  目标: $next_feature"
        echo ""

        if [ "$auto_confirm" != "1" ]; then
            echo -e "${YELLOW}按 Enter 继续，或 q 退出${NC}"
            stty sane 2>/dev/null
            read -r resp
            [ "$resp" = "q" ] && exit 0
        fi

        local feature_id
        feature_id=$(echo "$next_feature" | grep -o '\[F[0-9]*\]' | tr -d '[]')

        local begin_result
        begin_result=$(python3 "$FEATURE_CLI" begin "$feature_id" 2>&1) || {
            echo -e "${RED}错误: 无法开始功能 $feature_id${NC}"
            echo "  $begin_result"
            echo -e "${YELLOW}跳过此功能，继续下一个...${NC}"
            pending=$(python3 "$FEATURE_CLI" pending-count)
            continue
        }

        # ── Impact 分析（开发前基线）──
        local impact_script="$HARNESS_DIR/scripts/impact_analyzer.py"
        if [ -f "$impact_script" ]; then
            echo ""
            echo -e "${BLUE}[Impact] 分析当前代码状态作为基线...${NC}"
            python3 "$impact_script" 2>/dev/null || echo "  (impact 分析跳过)"
            echo ""
        fi

        # 获取功能上下文
        local context_info
        context_info=$(python3 "$FEATURE_CLI" context 2>/dev/null || echo "")

        # ── v2: 按任务类型选择 prompt 模板 ──
        local category=""
        if [ -n "$context_info" ]; then
            category=$(echo "$context_info" | grep '^CATEGORY=' | cut -d= -f2)
        fi

        local prompt_file="$HARNESS_DIR/prompts/session.txt"
        case "$category" in
            bugfix)
                local typed="$HARNESS_DIR/prompts/session_bugfix.txt"
                [ -f "$typed" ] && prompt_file="$typed"
                ;;
            feature|core|ui|api|database|auth)
                local typed="$HARNESS_DIR/prompts/session_feature.txt"
                [ -f "$typed" ] && prompt_file="$typed"
                ;;
            refactor|enhancement)
                local typed="$HARNESS_DIR/prompts/session_refactor.txt"
                [ -f "$typed" ] && prompt_file="$typed"
                ;;
        esac

        local log="$LOG_DIR/session_$(printf "%02d" $session_count)_$(date +%Y%m%d_%H%M%S).log"

        # ── Preflight 环境快照（v2: 减少前几轮探索性动作）──
        local preflight_context=""
        local preflight_script="$HARNESS_DIR/scripts/preflight.py"
        if [ -f "$preflight_script" ]; then
            preflight_context=$(python3 "$preflight_script" --prompt --save 2>/dev/null || echo "")
        fi

        # 获取最近 git commit（preflight 已包含，保留为兼容降级）
        local git_context=""
        if [ -z "$preflight_context" ] && [ -d ".git" ]; then
            git_context=$(git log --oneline -3 2>/dev/null | head -3)
        fi

        # 组装 prompt
        local prompt
        prompt="$(cat "$prompt_file")"

        # 注入 preflight 环境快照（最高优先级，放在最前面）
        if [ -n "$preflight_context" ]; then
            prompt="${prompt}

${preflight_context}
"
        fi

        # 注入功能上下文
        if [ -n "$context_info" ]; then
            prompt="${prompt}

## 当前功能上下文

\`\`\`
${context_info}
\`\`\`
"
        fi

        # 注入 git 历史（仅在无 preflight 时降级使用）
        if [ -n "$git_context" ]; then
            prompt="${prompt}

## 最近 Git 提交

\`\`\`
${git_context}
\`\`\`
"
        fi

        # 注入项目记忆
        if [ -f "$HARNESS_DIR/memory/project.json" ]; then
            local memory_context
            memory_context=$(python3 "$FEATURE_CLI" memory export 2>/dev/null || echo "")
            if [ -n "$memory_context" ]; then
                prompt="${prompt}

## 项目记忆

${memory_context}
"
            fi
        fi

        if [ "$interactive" = "1" ]; then
            run_claude "interactive" "$prompt" "$log"
        else
            run_claude "print" "$prompt" "$log"
        fi

        echo -e "${GREEN}会话 #$session_count 完成${NC}"

        pending=$(python3 "$FEATURE_CLI" pending-count)
        echo "  剩余: $pending"

        if [ "$pending" -gt 0 ] && [ "$session_count" -lt "$max_sessions" ]; then
            sleep 3
        fi
    done

    echo ""
    echo -e "${CYAN}── 循环结束 ─────────────────────────────────${NC}"
    echo "  会话数: $session_count"
    if [ "$pending" -eq 0 ]; then
        echo -e "${GREEN}  🎉 所有功能已完成！${NC}"
    else
        echo -e "${YELLOW}  还有 $pending 个功能待完成${NC}"
    fi
}

# ============================================================================
# status — 查看当前进度
# ============================================================================
cmd_status() {
    cd "$PROJECT_ROOT"

    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     Long-Running Agent · 项目状态         ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""

    if [ -d ".git" ]; then
        echo -e "${BLUE}Git 最近提交:${NC}"
        git log --oneline -5 2>/dev/null || echo "  暂无记录"
        echo ""
    fi

    if [ -f "$HARNESS_DIR/features.json" ] || [ -f "$HARNESS_DIR/feature_list.json" ]; then
        echo -e "${BLUE}功能概览:${NC}"
        python3 "$FEATURE_CLI" status
        echo ""
        echo -e "${BLUE}待开发:${NC}"
        python3 "$FEATURE_CLI" list --status pending
        echo ""
        echo -e "${BLUE}进行中:${NC}"
        python3 "$FEATURE_CLI" list --status in_progress
    else
        echo -e "${YELLOW}功能清单不存在${NC}"
        echo "  创建: .harness/dev.sh plan"
        echo "  迁移: .harness/dev.sh migrate"
    fi
}

# ============================================================================
# env — 初始化开发环境（自动检测项目类型）
# ============================================================================
cmd_env() {
    setup_cleanup
    cd "$PROJECT_ROOT"

    echo -e "${BLUE}[1/3] 基础工具检查${NC}"
    local ok=true
    command -v git &>/dev/null  && echo -e "  ${GREEN}✓${NC} git"  || { echo -e "  ${RED}✗ git${NC}";  ok=false; }
    command -v python3 &>/dev/null && echo -e "  ${GREEN}✓${NC} python3" || echo -e "  ${YELLOW}⚠ python3 未安装${NC}"
    command -v node &>/dev/null    && echo -e "  ${GREEN}✓${NC} node"    || echo -e "  ${YELLOW}⚠ node 未安装${NC}"
    [ "$ok" = false ] && exit 1
    echo ""

    echo -e "${BLUE}[2/3] 版本控制${NC}"
    if [ ! -d ".git" ]; then
        git init && echo -e "  ${GREEN}✓${NC} 已初始化 git"
    else
        echo -e "  ${GREEN}✓${NC} git 已存在 ($(git branch --show-current 2>/dev/null || echo 'detached'))"
    fi
    echo ""

    echo -e "${BLUE}[3/3] 项目依赖${NC}"
    if [ -f "requirements.txt" ]; then
        echo "  检测到 Python 项目"
        if [ ! -d "venv" ]; then
            python3 -m venv venv && echo -e "  ${GREEN}✓${NC} 虚拟环境已创建"
        fi
        source venv/bin/activate 2>/dev/null || true
        pip install -r requirements.txt --quiet && echo -e "  ${GREEN}✓${NC} pip 依赖已安装"
    elif [ -f "package.json" ]; then
        echo "  检测到 Node.js 项目"
        npm install && echo -e "  ${GREEN}✓${NC} npm 依赖已安装"
    elif [ -f "go.mod" ]; then
        echo "  检测到 Go 项目"
        go mod download && echo -e "  ${GREEN}✓${NC} go 依赖已下载"
    elif [ -f "Cargo.toml" ]; then
        echo "  检测到 Rust 项目"
        cargo fetch && echo -e "  ${GREEN}✓${NC} cargo 依赖已获取"
    else
        echo -e "  ${YELLOW}未检测到依赖文件，跳过安装${NC}"
    fi

    echo ""
    echo -e "${GREEN}✅ 环境就绪${NC}"
}

# ============================================================================
# 分发
# ============================================================================
usage() {
    echo "Long-Running Agent 开发系统"
    echo ""
    echo "用法: $(basename "$0") <command> [options]"
    echo ""
    echo "命令:"
    echo "  plan       从 requirements.md 生成功能清单"
    echo "  migrate    从现有代码库迁移到工作流"
    echo "  run        自动循环开发 (--auto 无人值守, --print 非交互, -n N 最大会话数)"
    echo "  status     查看当前进度"
    echo "  env        初始化开发环境 (自动检测项目类型)"
    echo ""
    echo "迭代模式:"
    echo "  add        添加迭代需求到功能清单"
    echo "             用法: dev.sh add <文档路径> [--type bugfix|feature|enhancement] [--force]"
    echo ""
    echo "质量保证:"
    echo "  lint       代码规范检查 [--fix 自动修复] [--json]"
    echo "  garden     技术债管理 [--auto] [--create-todos] [--json]"
    echo "  doctor     项目健康检查"
    echo "  impact     代码变更影响范围分析 [--staged|--commit] [--tests|--json]"
    echo ""
    echo "记忆系统:"
    echo "  remember   记录设计决策"
    echo "             用法: dev.sh remember <决策主题> <决策原因>"
    echo "  memory     记忆系统管理 (status/show/add/search/export)"
    echo ""
    echo "环境变量:"
    echo "  INTERACTIVE=0    非交互模式 (--print + tee)"
    echo "  CLAUDE_CMD=...   指定 Claude 命令路径"
    echo ""
}

# 启动时静默检查版本（不影响功能）
check_harness_version 2>/dev/null

case "${1:-}" in
    plan)    shift; cmd_plan "$@" ;;
    migrate) shift; cmd_migrate "$@" ;;
    run)     shift; cmd_run "$@" ;;
    status)  shift; cmd_status "$@" ;;
    env)     shift; cmd_env "$@" ;;
    add)     shift; cmd_add "$@" ;;
    remember) shift; cmd_remember "$@" ;;
    memory)  shift; cmd_memory "$@" ;;
    lint)    shift; cmd_lint "$@" ;;
    garden)  shift; cmd_garden "$@" ;;
    doctor)  shift; cmd_doctor "$@" ;;
    impact)  shift; cmd_impact "$@" ;;
    -h|--help) usage ;;
    *)       usage; exit 1 ;;
esac
