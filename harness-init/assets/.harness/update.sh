#!/bin/bash
# Harness 框架安全更新脚本
# 保留用户数据，仅更新框架文件

set -e

HARNESS_SRC="$HOME/.claude/skills/harness-init/assets/.harness"
HARNESS_DIR="./.harness"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Harness 框架安全更新                  ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# --check 模式：仅比对版本，不执行更新
# ============================================================================
if [ "${1:-}" = "--check" ]; then
    # 读取当前项目版本
    CURRENT_VERSION="unknown"
    if [ -f "$HARNESS_DIR/VERSION" ]; then
        CURRENT_VERSION=$(cat "$HARNESS_DIR/VERSION" | tr -d '[:space:]')
    fi

    # 读取源版本
    LATEST_VERSION="unknown"
    if [ -f "$HARNESS_SRC/VERSION" ]; then
        LATEST_VERSION=$(cat "$HARNESS_SRC/VERSION" | tr -d '[:space:]')
    fi

    # 使用 Python 做语义化版本比较（不依赖第三方库）
    NEED_UPDATE=$(python3 -c "
def parse_ver(v):
    return [int(''.join(c for c in p if c.isdigit()) or '0') for p in v.split('.')]
cur = parse_ver('$CURRENT_VERSION'.split('-')[0])
lat = parse_ver('$LATEST_VERSION'.split('-')[0])
for i in range(max(len(cur), len(lat))):
    a = cur[i] if i < len(cur) else 0
    b = lat[i] if i < len(lat) else 0
    if b > a:
        print('yes')
        break
    elif b < a:
        print('no')
        break
else:
    print('no')
" 2>/dev/null || echo "yes")

    # 输出结果（同时打印便于脚本解析）
    if [ "$NEED_UPDATE" = "yes" ]; then
        echo -e "${YELLOW}发现新版本!${NC}"
        echo "  当前版本: ${RED}$CURRENT_VERSION${NC}"
        echo "  最新版本: ${GREEN}$LATEST_VERSION${NC}"
        echo ""
        echo "运行以下命令更新:"
        echo "  ~/.claude/skills/harness-init/assets/.harness/update.sh"
        exit 0
    else
        echo -e "${GREEN}框架已是最新版本: $CURRENT_VERSION${NC}"
        exit 0
    fi
fi

# 检查是否存在 .harness 目录
if [ ! -d "$HARNESS_DIR" ]; then
    echo -e "${RED}错误: 当前目录没有 .harness 目录${NC}"
    echo "请在新项目目录中运行此脚本，或先运行 harness-init"
    exit 1
fi

# ============================================================================
# Step 1: 备份用户数据
# ============================================================================
echo -e "${YELLOW}Step 1: 备份用户数据...${NC}"
BACKUP_DIR="./.harness_update_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 需要保留的文件（用户数据）
PRESERVE_FILES=(
    "features.json"
    "config.json"
    ".features.lock"
)

# 需要保留的目录（用户数据）
PRESERVE_DIRS=(
    ".backups"
    "logs"
    "memory"  # 项目记忆，包含用户的设计决策
)

# 备份
for file in "${PRESERVE_FILES[@]}"; do
    if [ -f "$HARNESS_DIR/$file" ]; then
        cp "$HARNESS_DIR/$file" "$BACKUP_DIR/"
        echo "  ✓ 已备份 $file"
    fi
done

for dir in "${PRESERVE_DIRS[@]}"; do
    if [ -d "$HARNESS_DIR/$dir" ]; then
        cp -r "$HARNESS_DIR/$dir" "$BACKUP_DIR/"
        echo "  ✓ 已备份 $dir/"
    fi
done

echo -e "${GREEN}备份完成: $BACKUP_DIR${NC}"
echo ""

# ============================================================================
# Step 2: 更新框架文件
# ============================================================================
echo -e "${YELLOW}Step 2: 更新框架核心文件...${NC}"

# 需要更新的核心文件
UPDATE_FILES=(
    "feature_cli.py"
    "dev.sh"
    "_common.sh"
    "INSTRUCTIONS.md"
    "ITERATION_SPEC.md"
    "QUICKREF.md"
)

for file in "${UPDATE_FILES[@]}"; do
    if [ -f "$HARNESS_SRC/$file" ]; then
        # 检查是否在保留列表中
        if [[ " ${PRESERVE_FILES[@]} " =~ " $file " ]]; then
            echo -e "${YELLOW}  跳过 $file（已在保留列表）${NC}"
        else
            cp "$HARNESS_SRC/$file" "$HARNESS_DIR/"
            echo "  ✓ 已更新 $file"
        fi
    fi
done

# ============================================================================
# Step 2.5: 更新 prompts 目录
# ============================================================================
echo ""
echo -e "${YELLOW}Step 2.5: 更新 prompts 目录...${NC}"

if [ -d "$HARNESS_SRC/prompts" ]; then
    mkdir -p "$HARNESS_DIR/prompts"

    # 更新 session.txt（精简版）
    if [ -f "$HARNESS_SRC/prompts/session.txt" ]; then
        cp "$HARNESS_SRC/prompts/session.txt" "$HARNESS_DIR/prompts/"
        echo "  ✓ 已更新 prompts/session.txt"
    fi

    # 更新其他 prompt 文件
    for prompt_file in initializer.txt migration.txt session_bugfix.txt session_feature.txt session_refactor.txt; do
        if [ -f "$HARNESS_SRC/prompts/$prompt_file" ]; then
            cp "$HARNESS_SRC/prompts/$prompt_file" "$HARNESS_DIR/prompts/"
            echo "  ✓ 已更新 prompts/$prompt_file"
        fi
    done
fi

# ============================================================================
# Step 2.6: 新增 scripts 目录（代码质量工具）
# ============================================================================
echo ""
echo -e "${YELLOW}Step 2.6: 安装代码质量工具...${NC}"

if [ -d "$HARNESS_SRC/scripts" ]; then
    mkdir -p "$HARNESS_DIR/scripts"

    # 复制所有脚本
    for script in "$HARNESS_SRC/scripts"/*.py; do
        if [ -f "$script" ]; then
            script_name=$(basename "$script")
            cp "$script" "$HARNESS_DIR/scripts/"
            echo "  ✓ 已安装 scripts/$script_name"
        fi
    done
fi

# ============================================================================
# Step 2.65: 更新 lib 目录（feature_cli 模块化拆分）
# ============================================================================
echo ""
echo -e "${YELLOW}Step 2.65: 更新 lib 目录...${NC}"

if [ -d "$HARNESS_SRC/lib" ]; then
    mkdir -p "$HARNESS_DIR/lib"

    for lib_file in "$HARNESS_SRC/lib"/*.py; do
        if [ -f "$lib_file" ]; then
            lib_name=$(basename "$lib_file")
            cp "$lib_file" "$HARNESS_DIR/lib/"
            echo "  ✓ 已更新 lib/$lib_name"
        fi
    done
fi

# ============================================================================
# Step 2.7: 新增配置文件
# ============================================================================
echo ""
echo -e "${YELLOW}Step 2.7: 更新配置文件...${NC}"

# 黄金原则（总是更新）
if [ -f "$HARNESS_SRC/GOLDEN_RULES.md" ]; then
    cp "$HARNESS_SRC/GOLDEN_RULES.md" "$HARNESS_DIR/"
    echo "  ✓ 已更新 GOLDEN_RULES.md"
fi

# 架构配置（仅当不存在时添加，避免覆盖用户配置）
if [ -f "$HARNESS_SRC/architecture.json" ]; then
    if [ ! -f "$HARNESS_DIR/architecture.json" ]; then
        cp "$HARNESS_SRC/architecture.json" "$HARNESS_DIR/"
        echo "  ✓ 已添加 architecture.json"
    else
        echo -e "${YELLOW}  跳过 architecture.json（已存在，保留用户配置）${NC}"
    fi
fi

# ============================================================================
# Step 2.8: 合并 memory 目录
# ============================================================================
echo ""
echo -e "${YELLOW}Step 2.8: 合并 memory 目录...${NC}"
if [ -d "$HARNESS_SRC/memory" ]; then
    mkdir -p "$HARNESS_DIR/memory"

    # 需要确保存在的模板文件（仅在不存在时添加，保留用户数据）
    MEMORY_TEMPLATES=(
        "structure.md"
        "interfaces.md"
        "decisions.md"
        "project.json"
        "anti_patterns.json"
    )

    for template in "${MEMORY_TEMPLATES[@]}"; do
        if [ -f "$HARNESS_SRC/memory/$template" ] && [ ! -f "$HARNESS_DIR/memory/$template" ]; then
            cp "$HARNESS_SRC/memory/$template" "$HARNESS_DIR/memory/"
            echo "  ✓ 已添加 memory/$template"
        fi
    done
fi

# ============================================================================
# Step 2.85: v2 评测框架
# ============================================================================
echo ""
echo -e "${YELLOW}Step 2.85: 安装评测框架 (v2)...${NC}"

if [ -d "$HARNESS_SRC/bench" ]; then
    mkdir -p "$HARNESS_DIR/bench/tasks" "$HARNESS_DIR/bench/results"

    # 更新 eval.py 和 README
    for bench_file in eval.py README.md; do
        if [ -f "$HARNESS_SRC/bench/$bench_file" ]; then
            cp "$HARNESS_SRC/bench/$bench_file" "$HARNESS_DIR/bench/"
            echo "  ✓ 已安装 bench/$bench_file"
        fi
    done

    # 仅添加新的示例任务（不覆盖用户自定义任务）
    for task_file in "$HARNESS_SRC/bench/tasks"/*.json; do
        if [ -f "$task_file" ]; then
            task_name=$(basename "$task_file")
            if [ ! -f "$HARNESS_DIR/bench/tasks/$task_name" ]; then
                cp "$task_file" "$HARNESS_DIR/bench/tasks/"
                echo "  ✓ 已添加 bench/tasks/$task_name"
            fi
        fi
    done
fi

# ============================================================================
# Step 2.9: 更新 update.sh 自身和 VERSION 文件
# ============================================================================
if [ -f "$HARNESS_SRC/update.sh" ]; then
    cp "$HARNESS_SRC/update.sh" "$HARNESS_DIR/"
    echo "  ✓ 已更新 update.sh"
fi

if [ -f "$HARNESS_SRC/VERSION" ]; then
    cp "$HARNESS_SRC/VERSION" "$HARNESS_DIR/"
    echo "  ✓ 已更新 VERSION"
fi

# ============================================================================
# Step 3: 更新 CLAUDE.md
# ============================================================================
echo ""
echo -e "${YELLOW}Step 3: 更新 CLAUDE.md...${NC}"

CLAUDE_MD="./CLAUDE.md"
CLAUDE_TEMPLATE="$HOME/.claude/skills/harness-init/assets/CLAUDE.md.template"

if [ -f "$CLAUDE_MD" ]; then
    # 检查是否已经包含 Harness 开发规范
    if grep -q "## 功能开发工具" "$CLAUDE_MD"; then
        echo -e "${YELLOW}  CLAUDE.md 已包含 Harness 开发规范，跳过${NC}"
    else
        # 备份现有 CLAUDE.md
        cp "$CLAUDE_MD" "$BACKUP_DIR/CLAUDE.md.backup"

        # 追加内容
        echo -e "\n---\n\n# Harness 开发规范\n" >> "$CLAUDE_MD"
        cat "$CLAUDE_TEMPLATE" >> "$CLAUDE_MD"
        echo -e "${GREEN}  ✓ 已追加 Harness 开发规范到 CLAUDE.md${NC}"
    fi
else
    # 创建新文件
    cp "$CLAUDE_TEMPLATE" "$CLAUDE_MD"
    echo -e "${GREEN}  ✓ 已创建 CLAUDE.md${NC}"
fi

# ============================================================================
# Step 4: 验证更新
# ============================================================================
echo ""
echo -e "${YELLOW}Step 4: 验证更新...${NC}"

VERIFY_ERROR=0

# 检查关键文件
if [ ! -f "$HARNESS_DIR/features.json" ]; then
    if [ -f "$BACKUP_DIR/features.json" ]; then
        echo -e "${RED}  ✗ features.json 丢失！从备份恢复...${NC}"
        cp "$BACKUP_DIR/features.json" "$HARNESS_DIR/"
    else
        echo -e "${YELLOW}  ⚠ features.json 不存在（可能是新项目）${NC}"
    fi
else
    echo -e "${GREEN}  ✓ features.json 存在${NC}"
fi

if [ ! -d "$HARNESS_DIR/.backups" ]; then
    if [ -d "$BACKUP_DIR/.backups" ]; then
        echo -e "${RED}  ✗ .backups/ 丢失！从备份恢复...${NC}"
        cp -r "$BACKUP_DIR/.backups" "$HARNESS_DIR/"
    else
        echo -e "${YELLOW}  ⚠ .backups/ 不存在（可能是新项目）${NC}"
        mkdir -p "$HARNESS_DIR/.backups"
    fi
else
    echo -e "${GREEN}  ✓ .backups/ 存在${NC}"
fi

# 检查新文件
for check_file in "scripts/linter.py" "scripts/garden.py" "scripts/preflight.py" "GOLDEN_RULES.md" "bench/eval.py" "memory/anti_patterns.json"; do
    if [ -f "$HARNESS_DIR/$check_file" ]; then
        echo -e "${GREEN}  ✓ $check_file 已安装${NC}"
    else
        echo -e "${YELLOW}  ⚠ $check_file 未安装${NC}"
    fi
done

# 检查 v2 prompt 模板
for prompt_check in "prompts/session_bugfix.txt" "prompts/session_feature.txt" "prompts/session_refactor.txt"; do
    if [ -f "$HARNESS_DIR/$prompt_check" ]; then
        echo -e "${GREEN}  ✓ $prompt_check 已安装${NC}"
    fi
done

# ============================================================================
# 显示更新摘要
# ============================================================================
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              更新完成                      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}保留的文件:${NC}"
echo "  - features.json（功能清单和会话记录）"
echo "  - config.json（用户配置）"
echo "  - .backups/（自动备份）"
echo "  - logs/（会话日志）"
echo "  - memory/（项目记忆）"
echo ""
echo -e "${GREEN}更新的文件:${NC}"
echo "  - feature_cli.py（v2: 状态机约束 + 结构化日志 + 反模式）"
echo "  - dev.sh（v2: preflight 注入 + prompt 类型分流）"
echo "  - _common.sh, prompts/"
echo "  - INSTRUCTIONS.md, ITERATION_SPEC.md, QUICKREF.md"
echo ""
echo -e "${GREEN}新增的文件 (v2):${NC}"
echo "  - scripts/preflight.py（环境快照，减少探索轮次）"
echo "  - scripts/linter.py, scripts/garden.py"
echo "  - prompts/session_{bugfix,feature,refactor}.txt（类型化模板）"
echo "  - bench/eval.py（A/B 评测对比）"
echo "  - memory/anti_patterns.json（失败反模式自动归类）"
echo "  - GOLDEN_RULES.md, architecture.json"
echo ""
echo -e "${GREEN}新增能力:${NC}"
echo "  - Preflight 环境快照（session 前自动注入工作区状态）"
echo "  - Prompt 按任务类型分流（bugfix/feature/refactor）"
echo "  - fail --blocked（区分外部阻塞和可继续中断）"
echo "  - log -t error/decision（结构化日志类型）"
echo "  - report（v2 关键指标：中断/多次尝试/有效会话率）"
echo "  - bench eval（A/B 评测闭环）"
echo ""
echo -e "备份位置: ${YELLOW}$BACKUP_DIR${NC}"
echo ""
echo -e "${GREEN}建议: 检查更新后提交 git${NC}"
echo "  git add .harness CLAUDE.md"
echo "  git commit -m 'chore: 更新 harness 框架'"
