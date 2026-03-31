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

### task-notify — 任务完成提醒

> **类比**：Claude 完成长任务后的"闹钟"，语音 + 通知双保险

**你是否有这些困扰？**

| 场景 | task-notify 如何解决 |
|------|---------------------|
| ⏳ 长任务执行时走神去刷手机 | 语音播报 + 系统通知，想 miss 都难 |
| 🔔 终端通知经常被系统静默 | 使用 `terminal-notifier`，确保通知弹出 |
| 📋 不知道具体完成了什么 | 动态标题显示任务名、阶段、耗时 |

**快速开始**：
```bash
/notify                  # 发送默认通知
/notify 部署完成         # 自定义消息
```

**触发方式**（无需命令）：
> "任务完成后提醒我"
>
> "好了叫我一声"

**核心能力**：
- 语音播报（macOS `say` 命令）
- 系统通知（`terminal-notifier`）
- 动态标题（从上下文提取任务名）

---

### build-agent-team — Agent Team 构建框架

> **类比**：多 Agent 协作的"项目经理"，标准化团队创建流程

**适用场景**：

| 场景 | 说明 |
|------|------|
| 🔀 并行模块化开发 | 前端 + 后端 + 数据库 + 测试，无重叠编辑 |
| 🔍 多维度评审 | 安全 + 性能 + 可维护性 + 测试覆盖 |
| 🐛 竞争性调试 | 多个互斥假设并行验证 |
| 🔗 跨层协同 | 端到端变更，职责边界清晰 |

**快速开始**：
```bash
/build-agent-team 构建 Node.js 用户管理 CLI，包含 CRUD、权限控制
```

**核心能力**：
- 角色映射（前端/后端/测试/架构师...）
- 文件所有权规则（零冲突保证）
- 质量门禁（测试覆盖 / 安全扫描）
- 完成通知（项目名 + 阶段 + 耗时）

---

### git-proxy — Git 网络代理管理

> **类比**：Git 网络问题的"一键开关"，自动检测系统代理

**你是否有这些困扰？**

| 场景 | git-proxy 如何解决 |
|------|---------------------|
| 🌐 Git clone/push 超时 | 一键开启代理，自动检测系统配置 |
| 🔀 HTTP 和 SOCKS 代理切换 | 智能选择 SOCKS5（更快）或 HTTP |
| ❓ 不知道当前代理状态 | `status` 命令清晰展示 |
| 🔄 频繁开关代理 | `toggle` 一键切换 |

**快速开始**：
```bash
/git-proxy          # 查看状态
/git-proxy on       # 开启代理（自动检测）
/git-proxy off      # 关闭代理
/git-proxy toggle   # 切换状态
/git-proxy socks    # 强制使用 SOCKS5
```

**触发方式**（无需命令）：
> "git 代理设置一下"
>
> "切换 git 代理"

**核心能力**：
- 自动检测系统代理（环境变量 → macOS 网络设置 → 常见端口）
- 支持 HTTP/SOCKS5 代理
- 智能优先 SOCKS5（性能更好）

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
ln -sf $(pwd)/task-notify ~/.claude/skills/task-notify
ln -sf $(pwd)/build-agent-team ~/.claude/skills/build-agent-team
ln -sf $(pwd)/git-proxy ~/.claude/skills/git-proxy
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
├── task-notify/         # 任务完成提醒
│   └── SKILL.md
├── build-agent-team/    # Agent Team 构建框架
│   ├── SKILL.md
│   └── learning_system/ # 团队模板学习模块
├── git-proxy/           # Git 网络代理管理
│   └── SKILL.md
└── README.md
```
