# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个专门开发 Claude Code Skills 的项目。每个 skill 是一个独立目录，包含 `SKILL.md` 文件和可选的支持文件。

## Skills 存储位置

| 位置 | 路径 | 适用范围 |
|------|------|----------|
| Enterprise | 管理设置 | 组织内所有用户 |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` | 所有项目 |
| Project | `.claude/skills/<skill-name>/SKILL.md` | 仅当前项目 |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` | 插件启用处 |

**优先级**：enterprise > personal > project。Plugin skills 使用 `plugin-name:skill-name` 命名空间，不会冲突。

## Skill 目录结构

```
my-skill/
├── SKILL.md           # 必需 - 主指令文件
├── template.md        # 可选 - 模板文件
├── examples.md        # 可选 - 示例输出
├── reference.md       # 可选 - 详细参考文档
└── scripts/           # 可选 - 脚本文件
    └── helper.py
```

**规则**：保持 `SKILL.md` 在 500 行以内，详细内容移到支持文件中。

## SKILL.md 格式规范

### Frontmatter 字段参考

```markdown
---
name: my-skill
description: "功能描述，用于触发匹配"
argument-hint: "[参数提示]"
disable-model-invocation: false
user-invocable: true
allowed-tools: Read, Grep, Glob
model: claude-sonnet-4-6
context: fork
agent: Explore
---
```

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | 否 | 显示名称，省略则用目录名。仅小写字母、数字、连字符（最多64字符） |
| `description` | **推荐** | 功能描述，Claude 用此决定何时使用。省略则用首段内容 |
| `argument-hint` | 否 | 自动完成时显示的参数提示，如 `[issue-number]` |
| `disable-model-invocation` | 否 | `true` 阻止 Claude 自动加载，仅手动 `/name` 触发 |
| `user-invocable` | 否 | `false` 从 `/` 菜单隐藏，用于后台知识 |
| `allowed-tools` | 否 | skill 激活时无需权限的工具列表 |
| `model` | 否 | 指定使用的模型 |
| `context` | 否 | 设为 `fork` 在子代理中运行 |
| `agent` | 否 | `context: fork` 时使用的子代理类型（Explore、Plan、general-purpose） |
| `hooks` | 否 | skill 生命周期钩子 |

### 字符串替换

| 变量 | 说明 |
|------|------|
| `$ARGUMENTS` | 所有参数。若未使用此变量，参数会追加为 `ARGUMENTS: <value>` |
| `$ARGUMENTS[N]` | 按索引访问参数，如 `$ARGUMENTS[0]` 为第一个参数 |
| `$N` | `$ARGUMENTS[N]` 的简写，如 `$0`、`$1` |
| `${CLAUDE_SESSION_ID}` | 当前会话 ID |

### 动态上下文注入

使用 `!`command`` 语法在发送给 Claude 之前执行 shell 命令：

```markdown
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

### 在子代理中运行

设置 `context: fork` 让 skill 在隔离环境中运行：

```markdown
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly:

1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

可用 agent 类型：`Explore`、`Plan`、`general-purpose` 或自定义 subagent。

## 控制调用权限

| Frontmatter | 用户可调用 | Claude 可调用 | 上下文加载时机 |
|-------------|-----------|---------------|----------------|
| (默认) | Yes | Yes | 描述始终在上下文，调用时加载完整内容 |
| `disable-model-invocation: true` | Yes | No | 描述不在上下文，用户调用时加载 |
| `user-invocable: false` | No | Yes | 描述始终在上下文，调用时加载完整内容 |

### 限制工具访问

```markdown
---
name: safe-reader
description: Read files without making changes
allowed-tools: Read, Grep, Glob
---
```

## 开发工作流

### 创建新 Skill

1. 创建目录：`mkdir -p <skill-name>`
2. 创建 `SKILL.md`，包含 frontmatter 和指令内容
3. 测试触发：匹配 description 或直接 `/skill-name`
4. 添加支持文件（可选）：在 SKILL.md 中引用

### 部署 Skill

```bash
# 符号链接（推荐）
ln -s $(pwd)/<skill-name> ~/.claude/skills/<skill-name>

# 复制
cp -r <skill-name> ~/.claude/skills/
```

### 分享 Skill

- **Project skills**：将 `.claude/skills/` 提交到版本控制
- **Plugins**：在插件中创建 `skills/` 目录
- **Managed**：通过管理设置部署到组织

## 故障排除

### Skill 未触发
1. 检查 description 是否包含用户自然会说的话
2. 验证 skill 出现在 "What skills are available?"
3. 尝试更匹配 description 的表达
4. 直接用 `/skill-name` 调用

### Skill 触发过于频繁
1. 让 description 更具体
2. 添加 `disable-model-invocation: true`

### Claude 看不到所有 skills
运行 `/context` 检查是否有 skills 被排除的警告。字符预算为上下文窗口的 2%，备用值为 16,000 字符。

覆盖限制：设置 `SLASH_COMMAND_TOOL_CHAR_BUDGET` 环境变量。

## 关键规则

1. **SKILL.md 必需** - 是 skill 的入口点
2. **description 推荐** - Claude 用此决定何时使用
3. **保持精简** - SKILL.md 保持在 500 行以内
4. **引用支持文件** - 在 SKILL.md 中说明其他文件的用途
5. **目录名即 skill 名** - name 字段省略时使用目录名
