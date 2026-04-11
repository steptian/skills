---
name: harness-init
description: "初始化 .harness 开发框架，集成代码修改影响范围评估和测试覆盖建议功能。触发词：'初始化新项目'、'harness init'、'更新 harness'、'分析影响范围'、'评估修改影响'"
argument-hint: "[新项目|更新|影响分析]"
---

# Harness 项目初始化

为 Claude Code 项目初始化 `.harness` 开发框架，支持 Long-Running Agent 工作流。

## 触发条件

当用户说以下短语时触发：
- "初始化新项目"、"项目初始化"、"创建新项目"、"新项目启动"
- "harness init"、"启动 harness"
- "更新 harness"、"harness update"、"升级 harness 框架"

## 执行流程

### 首先判断：新项目还是已有项目

检查项目是否已有 `.harness` 目录：

- **不存在** → 执行【新项目初始化流程】
- **已存在** → 询问用户：
  - "检测到项目已有 .harness 目录，是否要更新框架？（保留您的功能清单和会话记录）"
  - 用户确认 → 执行【已有项目更新流程】
  - 用户拒绝 → 跳过，不做任何操作

---

## 新项目初始化流程

### Step 1: 复制 .harness 框架

```bash
cp -r ~/.claude/skills/harness-init/assets/.harness ./.
```

框架包含 feature_cli.py（功能状态管理）、dev.sh（开发入口）、prompts/（模板）、scripts/（工具）、memory/（记忆）、bench/（评测）等。

> 完整目录结构见 `~/.claude/skills/harness-init/assets/.harness/`。

### Step 2: 同步项目入口文件

**AGENTS.md**（智能体入口）：

```bash
if [ -f "./AGENTS.md" ]; then
  # 追加 harness 指南到现有 AGENTS.md 末尾
  echo -e "\n## Harness 开发指南\n" >> ./AGENTS.md
  echo "见 .harness/QUICKREF.md 获取命令速查" >> ./AGENTS.md
else
  cp ~/.claude/skills/harness-init/assets/AGENTS.md.template ./AGENTS.md
fi
```

然后填充 AGENTS.md 中的占位符：
- `{{PROJECT_NAME}}` 和 `{{PROJECT_DESCRIPTION}}` → 用 Step 3 收集的信息
- `{{ARCHITECTURE_OVERVIEW}}` → 用 `ls -la` + 项目目录结构自动生成目录树
- `{{KEY_DIRECTORIES}}` → 扫描项目目录，生成"目录 | 职责"表格

**CLAUDE.md**（项目规范）：

```bash
if [ -f "./CLAUDE.md" ]; then
  if ! grep -q "## 功能开发工具" "./CLAUDE.md"; then
    echo -e "\n---\n\n# Harness 开发规范\n" >> ./CLAUDE.md
    cat ~/.claude/skills/harness-init/assets/CLAUDE.md.template >> ./CLAUDE.md
  fi
else
  cp ~/.claude/skills/harness-init/assets/CLAUDE.md.template ./CLAUDE.md
fi
```

### Step 3: 渐进式需求收集

检查 `.harness/.onboarding.json` 判断当前引导阶段：

```bash
if [ -f ".harness/.onboarding.json" ]; then
  PHASE=$(python3 -c "import json; print(json.load(open('.harness/.onboarding.json')).get('phase', 1))")
else
  PHASE=1
fi
echo "引导阶段: Phase $PHASE"
```

根据阶段执行对应收集：

**Phase 1 — 基础信息（首次运行，必答）**

使用 AskUserQuestion 收集：
- **项目名称**：简短标识
- **一句话描述**：项目做什么

收集后更新文件并推进阶段：
```bash
# 更新 .harness/memory/project.json 中的 name 和 description
# 更新 AGENTS.md 占位符 {{PROJECT_NAME}} 和 {{PROJECT_DESCRIPTION}}
# 更新 .harness/.onboarding.json: {"phase": 2, "project_name": "...", "project_description": "..."}
```

**Phase 2 — 功能需求（第二次触发）**

使用 AskUserQuestion 收集：
- **核心功能列表**：主要功能点（3-5 个）
- **技术栈偏好**：Python/Node.js/其他

收集后更新 `.harness/requirements.md` 并推进阶段：
```bash
# 将功能列表写入 .harness/requirements.md
# 更新 .harness/.onboarding.json: {"phase": 3, ...}
```

**Phase 3 — 初始化方式选择（第三次触发）**

让用户选择初始化方式：

| 方式 | 命令 | 适用场景 |
|------|------|----------|
| **plan** | `.harness/dev.sh plan` | 从需求文档生成功能清单（新项目） |
| **migrate** | `.harness/dev.sh migrate` | 从现有代码库迁移（已有代码） |
| **env** | `.harness/dev.sh env` | 仅初始化开发环境 |

执行选择后，更新阶段并提交 git：
```bash
# 更新 .harness/.onboarding.json: {"phase": "done", ...}
git add .harness AGENTS.md CLAUDE.md
git commit -m "feat: 初始化 harness 开发框架"
```

### Step 5: 非 git 项目保护

如果项目目录没有 `.git`，提醒用户：

> "当前项目不是 git 仓库。建议先运行 `git init` 或在初始化方式中选择 env（会自动初始化 git）。"

---

## 已有项目更新流程

### 版本检查（自动）

检测到已有 `.harness` 时，**首先比对版本号**：

```bash
# 读取项目当前版本
CURRENT=$(cat .harness/VERSION 2>/dev/null || echo "unknown")
# 读取源版本（最新）
LATEST=$(cat ~/.claude/skills/harness-init/assets/.harness/VERSION 2>/dev/null || echo "unknown")
echo "当前: $CURRENT → 最新: $LATEST"
```

然后判断：

- **版本相同** → 提示"框架已是最新版本，无需更新"，跳过
- **源版本更新** → 告知用户新版本号，询问是否升级
- **项目版本更新**（极少见）→ 提示"项目版本比源版本新，可能是开发版"
- **版本未知** → 建议执行更新以确保完整

也可以用 `update.sh --check` 做纯检查：

```bash
~/.claude/skills/harness-init/assets/.harness/update.sh --check
```

### 执行更新

用户确认后，使用 `update.sh` 脚本安全更新：

```bash
~/.claude/skills/harness-init/assets/.harness/update.sh
```

更新过程：备份用户数据 → 更新框架文件 → 同步 CLAUDE.md → 验证完整性。

---

## 开发流程集成（新增）

### 在 begin 时自动运行 impact 分析

`dev.sh run` 命令已优化，在每次会话开始（`feature_cli.py begin`）后自动运行 impact 分析：

1. **开发前基线分析** - 记录开发前的代码状态
2. **上下文感知** - AI 在开发过程中了解当前状态
3. **变更对比** - 可对比开发前后的影响范围变化

### AI 辅助开发

session prompt 已更新，AI 在开发过程中会：
- 知道 impact 分析工具的存在和用法
- 在修改核心模块前主动分析影响范围
- 在提交代码前确认需要运行的测试
- 在 refactor 任务中验证依赖关系

---

## 代码修改影响范围分析（新增）

### 功能概述

`impact_analyzer.py` 脚本用于分析代码变更的影响范围，帮助开发者在修改代码后：
- 了解哪些文件会受到直接或间接影响
- 识别需要运行的相关测试
- 评估变更风险等级
- 获得测试覆盖建议

### 使用方法

```bash
# 分析所有变更（staged + unstaged）
.harness/dev.sh impact

# 分析已暂存变更
.harness/dev.sh impact --staged

# 分析指定提交
.harness/dev.sh impact --commit HEAD~1

# 仅输出测试建议
.harness/dev.sh impact --tests

# JSON 格式输出
.harness/dev.sh impact --json
```

### 分析内容

1. **变更文件检测**
   - 检测新增、修改、删除、重命名的文件
   - 显示变更类型图标

2. **依赖关系分析**
   - 分析 Python/TypeScript/JavaScript 的 import 关系
   - 构建依赖图
   - 找出直接受影响的文件

3. **传递影响计算**
   - 递归计算所有间接受影响的文件
   - 显示影响范围汇总

4. **受影响测试识别**
   - 根据变更文件查找相关测试
   - 支持常见测试命名模式（test_*, *_test*, *.spec.*, *.test.*）

5. **风险等级评估**
   - 根据变更文件数量、受影响范围、核心文件变更等评估风险
   - 风险等级：低风险（🟢）、中等风险（🟡）、高风险（🔴）

6. **测试建议**
   - 列出需要运行的测试文件
   - 提供快速运行命令（pytest/npm test）

### 在开发流程中的应用

**修改代码前**：
```bash
# 预分析即将修改的文件的影响范围
# （先 git add 然后分析）
git add path/to/file.py
.harness/dev.sh impact --staged
```

**提交代码前**：
```bash
# 分析所有变更，确保没有遗漏的影响
.harness/dev.sh impact
```

**代码审查时**：
```bash
# 分析特定提交的影响范围
.harness/dev.sh impact --commit <commit-hash>
```

---

## 相关资源

- **命令速查**：`reference.md`（详细命令参考）
- **INSTRUCTIONS.md**：详细使用说明（在 `.harness/` 目录中）
- **QUICKREF.md**：快速参考手册
- **feature_cli.py**：所有状态操作必须通过此工具
- **impact_analyzer.py**：代码变更影响范围分析器（新增）

---

## 经验反思与规则进化（v2.3.0 新增）

### learn 命令 — 记录经验教训

```bash
# 记录一条教训
python3 .harness/feature_cli.py learn \
  --category "debugging" \
  --confidence 8 \
  --lesson "修改配置前先备份" \
  --context "直接改 config.json 导致格式损坏" \
  --feature-id F003

# 类别：debugging | architecture | workflow | testing | optimization
# 信心度：1-10，越高越确定普遍适用
```

教训存储在 `.harness/memory/learnings.json`，最多 100 条，自动淘汰低价值条目。

### 自动反思

`complete` 命令执行后，如果本次会话有日志记录，会自动输出反思提示（stderr）。
Claude 在场时会读取会话日志、提取教训、通过 `learn` 命令写入。

### begin 时注入教训

`begin` 命令执行后，自动加载最近 5 条高信心度（>=6）的历史教训，
帮助新会话站在之前的经验基础上。

### evolve 命令 — 规则进化建议

```bash
# 查看规则进化建议
python3 .harness/feature_cli.py evolve
```

扫描 `learnings.json` 和 `anti_patterns.json`，当同类教训出现 3 次以上时，
建议在 `GOLDEN_RULES.md` 中新增或强化规则。仅输出建议，不自动修改。
