# Claude Code Skills

个人开发的 Claude Code Skills 集合。

## Skills 列表

### know-keep - 知识提取器

从对话或项目中提取可复用知识并持久化存储。

```bash
/know-keep              # 扫描项目文档提取知识
/know-keep --chat       # 从当前对话提取（推荐日常使用）
/know-keep --sync       # 审查知识库，沉淀到 CLAUDE.md
/know-keep --compress   # 压缩整理知识库
```

**特性**：
- 分层存储（L0 索引 / L1 摘要 / L2 详情）
- Token 优化
- 自动触发（"记一下"、"记住这个"、"沉淀知识"）

## 使用方法

将 skill 目录链接到 Claude Code skills 目录：

```bash
ln -s $(pwd)/know-keep ~/.claude/skills/know-keep
```

## 开发规范

详见 [CLAUDE.md](./CLAUDE.md)（项目内）。
