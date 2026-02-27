# Claude Code Skills

个人开发的 Claude Code Skills 集合。

## Skills 列表

### daily-plan — AI 驱动的 GTD + 复盘系统

> **类比**：GTD × 时间块 × 数据复盘，由 Claude 智能编排

**你是否有这些困扰？**

| 场景 | daily-plan 如何解决 |
|------|---------------------|
| 🌅 每天早上不知道先做什么 | 四象限自动排序，🔴 重要紧急先做 |
| 📋 任务散落在多个项目/文档 | 自动扫描 `**/TODO.md` + 知识库关联 |
| ⏰ 总是低估任务时间 | 基于历史数据智能估算 |
| 🔄 同类任务反复延期 | 复盘识别"问题模式"，给出改进建议 |

**快速开始**：
```bash
/daily-plan              # 开始今日计划
/daily-plan --add "任务" # 快速添加
/daily-plan --done 1,2   # 标记完成
/daily-plan --review     # 每日复盘（识别延期模式）
/daily-plan --week       # 每周总结
```

**核心能力**：
- 四象限优先级（🔴/🟡/🟠/🟢）
- 多来源任务聚合（项目扫描 + 结转 + 用户输入）
- 智能时间估算（越用越准）
- 问题模式识别（"写文档"连续3天延期？）

---

### know-keep — Claude 的长期记忆

> **类比**：给 Claude 装上跨会话的长期记忆，但几乎不占上下文

**你是否有这些困扰？**

| 场景 | know-keep 如何解决 |
|------|---------------------|
| 🕳️ 同一个坑踩两次 | "记一下这个坑" → 永久记住 |
| 🧠 Claude 每次新会话都"失忆" | 知识库跨会话持久化 |
| 📚 项目文档太多，Claude 读不过来 | 三层存储，索引 <50 tokens |
| 💬 对话中有价值经验流失 | `--chat` 一键提取 |

**快速开始**：
```bash
/know-keep              # 扫描项目提取知识
/know-keep --chat       # 从当前对话提取（推荐）
/know-keep --sync       # 沉淀到 CLAUDE.md
```

**触发方式**（无需命令）：
> "记一下，macOS 显示隐藏文件用 `Cmd+Shift+.`"
>
> Claude 自动调用 know-keep 存储

**核心能力**：
- 自然语言触发（"记一下"、"沉淀知识"）
- 三层存储（L0索引 <50 tokens / L1摘要 / L2详情）
- 只提取可复用模式，拒绝项目特定内容

---

## 安装

```bash
# 安装全部
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
└── README.md
```
