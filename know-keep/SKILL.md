---
name: know-keep
description: "从对话或项目中提取可复用知识并持久化存储。当用户说'记一下'、'记住这个'、'沉淀知识'、'提取干货'、'保存经验'时触发。支持对话提取(--chat)、知识同步(--sync)、压缩整理(--compress)等模式。"
argument-hint: [--chat] [--sync] [--compress] [-c 类别]
model: sonnet
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(find *, wc)
---

# know-keep - 知识提取器

> **核心原则**: 提取可复用的抽象模式，不记录具体实现细节

## 快速开始

```bash
/know-keep              # 扫描项目文档提取知识
/know-keep --chat       # 从当前对话提取（推荐日常使用）
/know-keep --sync       # 审查知识库，沉淀到 CLAUDE.md
/know-keep --compress   # 压缩整理知识库
```

## 存储结构

```
~/.kb/                    # 默认路径，首次运行可配置
├── config.yaml           # 配置
├── index.yaml            # L0 索引（<50 tokens）
├── <category>.md         # L1 摘要
└── detail/               # L2 详情
```

**配置文件** (`~/.kb/config.yaml`):
```yaml
storage_path: ~/.kb
created: 2026-02-27
```

## 知识分层

| 层级 | 文件 | 用途 | Token |
|------|------|------|-------|
| L0 | index.yaml | 索引，自动加载 | <50 |
| L1 | *.md | 摘要，按需加载 | ~200/文件 |
| L2 | detail/ | 详情，极少使用 | 不限 |

## 提取标准

### 提取
- 设计模式、架构决策
- 踩坑经验、最佳实践
- 通用工具技巧、工作流

### 不提取
- 具体实现代码
- 项目特定配置
- 一次性决策

## 知识格式

```markdown
## [标题] ⭐(1-3)

> 一句话原则

**场景**: 适用场景
**示例**:
```
最小示例
```
---
来源: conversation | 提取: YYYY-MM-DD
```

## 执行流程

1. **检测模式**: --chat / --sync / --compress / 默认扫描
2. **提取知识**: 按标准筛选和抽象
3. **写入存储**: 更新 index.yaml 和对应文件
4. **输出报告**: 统计新增/合并条目

详细流程请参考 [reference.md](./reference.md)，示例输出见 [examples.md](./examples.md)。

## 输出格式

```
提取完成 | 模式: --chat
新增: 1 条 | 合并: 0 条
• macOS 隐藏文件显示 ⭐⭐
  > Cmd+Shift+. 切换
耗时: 5s | Token: ~800
```
