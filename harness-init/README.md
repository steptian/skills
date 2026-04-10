# harness-init — Claude Code 项目开发框架

> **一句话**：给任何项目装上标准化的 AI 开发工作流，从需求到交付全自动管理

## 它解决什么问题？

| 痛点 | harness-init 如何解决 |
|------|----------------------|
| 每个项目开发流程不统一 | 一键初始化标准框架，需求→开发→测试一条龙 |
| Claude 多次会话间状态丢失 | 功能状态机 + 会话记录，断点续开发 |
| 不知道改了什么、影响了哪里 | 代码变更影响范围分析 + 测试覆盖建议 |
| 技术债越积越多 | 技术债花园自动扫描 + 代码规范检查 |
| 框架更新怕丢数据 | 安全更新脚本，用户数据完整保留 |

## 快速开始

```bash
# 新项目初始化
/harness-init

# 检查框架版本
/harness-init 更新

# 分析代码变更影响
/harness-init 影响分析
```

**触发方式**（无需命令）：
> "初始化新项目"
>
> "harness init"
>
> "更新 harness"

## 框架包含什么

初始化后在项目中生成 `.harness/` 目录：

```
.harness/
├── feature_cli.py       # 功能状态管理（开始/完成/中断）
├── dev.sh               # 开发入口（plan/run/status/lint/impact）
├── _common.sh           # 公共模块
├── VERSION              # 版本号
├── prompts/             # 任务类型化模板
│   ├── session_bugfix.txt
│   ├── session_feature.txt
│   └── session_refactor.txt
├── scripts/             # 工具集
│   ├── impact_analyzer.py  # 代码变更影响分析
│   ├── linter.py           # 代码规范检查
│   ├── garden.py           # 技术债管理
│   └── preflight.py        # 环境快照
├── lib/                 # 核心模块
│   ├── core.py             # 安全IO + 版本管理
│   └── anti_patterns.py    # 反模式检测
├── memory/              # 项目记忆
├── bench/               # 评测框架
├── INSTRUCTIONS.md      # 详细使用说明
└── QUICKREF.md          # 快速参考
```

## 核心命令

### 开发流程

```bash
.harness/dev.sh plan                           # 从需求生成功能清单
.harness/dev.sh migrate                        # 从现有代码库迁移
.harness/dev.sh run                            # 自动循环开发
.harness/dev.sh run --auto -n 20               # 无人值守模式
.harness/dev.sh status                         # 查看进度
.harness/dev.sh add new_feature.md --type feature  # 添加新需求
```

### 质量保证

```bash
.harness/dev.sh impact                         # 代码变更影响分析
.harness/dev.sh impact --staged                # 分析已暂存变更
.harness/dev.sh lint                           # 代码规范检查
.harness/dev.sh lint --fix                     # 自动修复
.harness/dev.sh garden --auto                  # 技术债管理
.harness/dev.sh doctor                         # 项目健康检查
```

### 功能状态管理

```bash
python3 .harness/feature_cli.py begin F001     # 开始开发
python3 .harness/feature_cli.py log "完成XX"   # 记录进度
python3 .harness/feature_cli.py complete F001 -m "完成"
python3 .harness/feature_cli.py next           # 下一个待开发
python3 .harness/feature_cli.py report         # 进度报告
python3 .harness/feature_cli.py --version      # 查看版本
```

### 版本管理

```bash
# 检查是否有新版本
~/.claude/skills/harness-init/assets/.harness/update.sh --check

# 执行更新（保留用户数据）
~/.claude/skills/harness-init/assets/.harness/update.sh
```

每次使用 `dev.sh` 时会自动静默检查版本，过期时显示黄色提醒。

## 设计亮点

- **安全更新**：更新框架时自动备份 features.json、config.json、memory/ 等用户数据
- **版本感知**：启动时自动比对版本号，提醒升级（v2.2.0+）
- **影响分析**：修改代码后自动分析依赖链，识别受影响文件和测试
- **任务分流**：按 bugfix/feature/refactor 类型使用不同 prompt 模板
- **环境快照**：每次会话前自动注入工作区状态，减少探索性轮次
