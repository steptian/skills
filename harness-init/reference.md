# Harness 命令参考

## dev.sh 子命令

| 命令 | 作用 | 示例 |
|------|------|------|
| `plan` | 从需求文档生成功能清单 | `.harness/dev.sh plan` |
| `migrate` | 从现有代码库迁移 | `.harness/dev.sh migrate` |
| `run` | 自动循环开发 | `.harness/dev.sh run --auto -n 20` |
| `status` | 查看当前进度 | `.harness/dev.sh status` |
| `env` | 初始化开发环境 | `.harness/dev.sh env` |
| `add` | 添加迭代需求 | `.harness/dev.sh add bugfix.md --type bugfix` |
| `remember` | 记录设计决策 | `.harness/dev.sh remember "选择 JWT" "跨域场景"` |
| `memory` | 记忆系统管理 | `.harness/dev.sh memory status` |
| `lint` | 代码规范检查 | `.harness/dev.sh lint --fix` |
| `garden` | 技术债管理 | `.harness/dev.sh garden --auto` |
| `doctor` | 项目健康检查 | `.harness/dev.sh doctor` |
| `impact` | 代码变更影响范围分析 | `.harness/dev.sh impact --staged` |

## feature_cli.py 命令

```bash
# 核心命令
python3 .harness/feature_cli.py begin <FEATURE_ID>    # 开始开发
python3 .harness/feature_cli.py log "进度说明"         # 记录进度（无需ID）
python3 .harness/feature_cli.py log "发现问题" -t error  # 带类型的日志
python3 .harness/feature_cli.py complete <FEATURE_ID> -m "完成"
python3 .harness/feature_cli.py fail <FEATURE_ID> -m "中断原因"
python3 .harness/feature_cli.py fail <FEATURE_ID> --blocked -m "外部阻塞"

# 查询命令
python3 .harness/feature_cli.py status      # 统计概览
python3 .harness/feature_cli.py list        # 列出功能
python3 .harness/feature_cli.py next        # 下一个待开发
python3 .harness/feature_cli.py unblock     # 可开始的功能
python3 .harness/feature_cli.py deps        # 依赖树
python3 .harness/feature_cli.py report      # 进度报告

# 维护命令
python3 .harness/feature_cli.py stale --fix # 修复僵尸会话
python3 .harness/feature_cli.py recover     # 从备份恢复
python3 .harness/feature_cli.py --version   # 查看版本

# v2 评测
python3 .harness/bench/eval.py run --tag v1     # 运行评测
python3 .harness/bench/eval.py compare v1 v2    # A/B 对比
python3 .harness/bench/eval.py list             # 历史评测

# v2 环境快照（dev.sh run 时自动调用）
python3 .harness/scripts/preflight.py --prompt

# 影响范围分析
python3 .harness/scripts/impact_analyzer.py              # 分析所有变更
python3 .harness/scripts/impact_analyzer.py --staged     # 分析已暂存变更
python3 .harness/scripts/impact_analyzer.py --commit HEAD~1  # 分析指定提交
python3 .harness/scripts/impact_analyzer.py --tests      # 仅输出测试建议
python3 .harness/scripts/impact_analyzer.py --json       # JSON 格式输出
```

## 后续使用

初始化完成后，用户可以：

```bash
.harness/dev.sh status                          # 查看进度
.harness/dev.sh run                             # 自动循环开发
.harness/dev.sh run --auto -n 20                # 无人值守模式
.harness/dev.sh add new_feature.md --type feature  # 添加新需求
.harness/dev.sh remember "认证方案" "选择 JWT"      # 记录设计决策
.harness/dev.sh doctor                             # 健康检查
```

## 注意事项

- 确保 `claude` 命令已安装并可用
- 如果项目已有 `.harness` 目录，先检查版本号再决定是否更新
- 初始化后建议立即提交 git commit
- 使用 `update.sh` 进行安全更新，保留用户数据
- 使用 `update.sh --check` 仅检查版本，不执行更新

## 版本管理

```bash
# 查看当前版本
python3 .harness/feature_cli.py --version

# 检查是否有更新
~/.claude/skills/harness-init/assets/.harness/update.sh --check

# 执行更新
~/.claude/skills/harness-init/assets/.harness/update.sh
```
