# Claude Code Skills

个人开发的 Claude Code Skills 集合。

## Skills 列表

### daily-plan - 每日待办计划

四象限优先级 + 时段分配 + 智能估算 + 持续复盘。

```bash
/daily-plan              # 创建/查看今日计划
/daily-plan --add "任务" # 快速添加任务
/daily-plan --done 1,2   # 标记任务完成
/daily-plan --review     # 每日复盘
/daily-plan --week       # 每周总结
```

**特性**：
- 四象限分类（🔴重要紧急 / 🟡重要不紧急 / 🟠不重要紧急 / 🟢可不做）
- 时段分配（上午/下午/晚上）
- 智能时间估算（基于历史数据）
- 完整状态管理（待办/进行中/完成/延期/阻塞）
- 每日复盘 + 每周总结
- 完成率统计、问题模式识别、容量分析

---

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

## 安装

将 skill 目录链接到 Claude Code skills 目录：

```bash
# 安装全部 skills
for skill in */; do
  ln -sf "$(pwd)/$skill" ~/.claude/skills/"$skill"
done

# 或单独安装
ln -sf $(pwd)/daily-plan ~/.claude/skills/daily-plan
ln -sf $(pwd)/know-keep ~/.claude/skills/know-keep
```

## 目录结构

```
skills/
├── daily-plan/          # 每日待办计划
│   ├── SKILL.md
│   ├── reference.md
│   └── examples.md
├── know-keep/           # 知识提取器
│   ├── SKILL.md
│   ├── reference.md
│   └── examples.md
└── CLAUDE.md            # 开发规范（本地）
```

## 开发规范

详见 [CLAUDE.md](./CLAUDE.md)。
