# Long-Running Agent 指导文档

## 系统结构

```
.harness/
├── dev.sh               # 唯一入口（plan / migrate / run / status / env）
├── feature_cli.py       # 功能状态管理工具（v2: 状态机约束 + 结构化日志）
├── _common.sh           # Shell 公共模块
├── config.json          # 配置文件（可选）
├── prompts/             # Prompt 模板（v2: 按任务类型自动分流）
│   ├── session.txt      #   通用开发会话 prompt
│   ├── session_bugfix.txt    # Bug 修复专用
│   ├── session_feature.txt   # 新功能专用
│   ├── session_refactor.txt  # 重构专用
│   ├── initializer.txt  #   初始化 prompt
│   └── migration.txt    #   迁移 prompt
├── scripts/
│   ├── preflight.py     # v2: 环境快照（session 前自动采集）
│   ├── linter.py        # 代码规范检查
│   └── garden.py        # 技术债管理
├── bench/               # v2: 评测闭环
│   ├── eval.py          # A/B 对比脚本
│   └── tasks/           # 基准任务定义
├── memory/              # 记忆系统
│   ├── anti_patterns.json  # v2: 失败反模式自动归类
│   └── ...
├── features.json        # 单一数据源（功能 + 会话日志）
├── .backups/            # 自动备份（feature_cli.py 管理）
├── logs/                # 会话日志 + preflight 快照
├── requirements.md      # 用户需求
└── INSTRUCTIONS.md      # 本文件
```

## 快速开始

```bash
# 新项目：编辑需求 → 生成功能清单 → 循环开发
vim .harness/requirements.md
.harness/dev.sh plan
.harness/dev.sh run

# 现有项目：分析代码 → 生成功能清单 → 循环开发
.harness/dev.sh migrate
.harness/dev.sh run

# 查看进度
.harness/dev.sh status

# 初始化开发环境（自动检测项目类型）
.harness/dev.sh env
```

## 核心原则

### 1. 增量开发
- 每个会话只专注一个 feature
- 完成一个小功能比开始多个半成品更有价值

### 2. 单一数据源
- `features.json` 是唯一的状态文件，包含功能清单和会话日志
- **所有状态修改必须通过 `feature_cli.py`**，禁止直接编辑 JSON

### 3. 安全写入
- feature_cli.py 保证原子写入（不会出现半写状态）
- 文件锁防止并发冲突
- 每次写入自动备份到 `.backups/`

### 4. 上下文连续性
- 会话中断后，下次会话自动注入上下文信息
- 包括：上次进度、中断原因、最近 git 提交

## feature_cli.py 命令参考

```bash
CLI="python3 .harness/feature_cli.py"

# 基础命令
$CLI status                          # 统计概览
$CLI list [--status pending]         # 列出功能
$CLI next                            # 获取下一个（in_progress > pending 按优先级）
$CLI context                         # 输出下一个功能的上下文信息
$CLI pending-count                   # 未完成数量

# 开发流程
$CLI begin F001                      # 开始开发（v2: 并发硬约束，自动抢占旧会话）
$CLI log "进度说明"                   # 添加会话日志（v2: 结构化 ts/type/message）
$CLI log "发现问题" -t error          # v2: 带类型的日志（progress/error/decision/test）
$CLI complete F001 -m "说明"         # 标记完成
$CLI fail F001 -m "原因"             # 标记中断（v2: 自动记录 interrupt_count）
$CLI fail F001 --blocked -m "等待API"  # v2: 标记为外部阻塞

# 依赖管理
$CLI deps                            # 显示功能依赖树
$CLI unblock                         # 显示可以开始开发的功能

# 维护命令
$CLI stale [--hours 24] [--fix]      # 检测/修复僵尸会话
$CLI recover                         # 从备份恢复
$CLI config                          # 显示当前配置
$CLI report [--export report.json]   # 生成进度报告
```

## 会话工作流

```
1. feature_cli.py next       → 获取目标功能
2. feature_cli.py begin FXXX → 创建会话记录
3. 编写代码、测试
4. feature_cli.py log "..."  → 记录进度（可多次调用）
5. feature_cli.py complete FXXX -m "..." → 标记完成
6. git add . && git commit   → 提交代码
```

## 配置文件 (config.json)

```json
{
  "max_sessions": 10,
  "max_running_sessions": 1,
  "stale_hours": 24,
  "auto_commit": true,
  "claude_args": "--dangerously-skip-permissions",
  "interactive": true,
  "auto_confirm": false
}
```

## features.json 数据结构

```json
{
  "project": { "name": "", "description": "", "tech_stack": [] },
  "features": [
    {
      "id": "F001",
      "priority": "high|medium|low",
      "status": "pending|in_progress|completed|blocked",
      "passes": false,
      "description": "...",
      "steps": ["..."],
      "acceptance_criteria": ["..."],
      "dependencies": ["F000"],
      "interrupt_reason": "..."  // 中断原因（可选）
    }
  ],
  "sessions": [
    {
      "id": "SESSION-01",
      "feature_id": "F001",
      "started_at": "...",
      "ended_at": "...",
      "status": "completed|interrupted|running",
      "logs": ["..."]
    }
  ],
  "statistics": {}
}
```

## dev.sh 子命令参考

| 命令 | 作用 | 环境变量 |
|------|------|---------|
| `plan` | 从 requirements.md 生成功能清单 | |
| `migrate` | 从现有代码库迁移 | `INTERACTIVE=0` |
| `run` | 自动循环开发 | `MAX_SESSIONS=N`, `AUTO_CONFIRM=1`, `INTERACTIVE=0` |
| `status` | 查看当前进度 | |
| `env` | 初始化开发环境（自动检测） | |

`run` 额外参数：`--auto`（无人值守）、`-n 20`（最大会话数）

## 常见问题

**Q: 功能开发到一半上下文用完了？**
```bash
python3 .harness/feature_cli.py fail F001 -m "上下文不足"
git add . && git commit -m "wip: F001 进行中"
```
下个会话会自动获取上下文信息，继续开发。

**Q: features.json 被写坏了？**
```bash
python3 .harness/feature_cli.py recover
```

**Q: 有功能卡在 in_progress 很久没动？**
```bash
# 检测僵尸会话
python3 .harness/feature_cli.py stale

# 自动修复
python3 .harness/feature_cli.py stale --fix
```

**Q: 想看看哪些功能可以开始开发？**
```bash
python3 .harness/feature_cli.py unblock
```

**Q: 多个终端同时运行了 `dev.sh run`？**
feature_cli.py 使用文件锁，不会出现数据损坏。但建议只运行一个实例。

**Q: 想导出进度报告？**
```bash
python3 .harness/feature_cli.py report --export progress.json
```

**Q: 如何查看 v2 关键指标？**
```bash
python3 .harness/feature_cli.py report
# 在末尾会显示: 中断次数、多次尝试、有效会话率、完成率
```

**Q: 如何查看已知的失败模式？**
```bash
python3 .harness/feature_cli.py memory export
# 末尾会输出「已知失败模式」及对策
```

**Q: 如何运行 A/B 评测？**
```bash
python3 .harness/bench/eval.py run --tag v1    # 跑基线
# 改 prompt/流程后...
python3 .harness/bench/eval.py run --tag v2    # 跑新版
python3 .harness/bench/eval.py compare v1 v2   # 对比
```

**Q: 环境快照没生效？**
```bash
# 手动测试 preflight
python3 .harness/scripts/preflight.py --prompt
# 如果输出正常，dev.sh run 会自动注入
```
