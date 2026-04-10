# feature_cli.py 快速参考

## 命令速查表

| 命令 | 格式 | 说明 |
|------|------|------|
| **begin** | `begin <FEATURE_ID>` | 开始开发（v2: 并发硬约束） |
| **log** | `log "<message>"` | 记录进度（无需ID） |
| **log** | `log "<msg>" -t error` | v2: 带类型日志（progress/error/decision/test） |
| **complete** | `complete <FEATURE_ID> -m "<msg>"` | 标记完成 |
| **fail** | `fail <FEATURE_ID> -m "<reason>"` | 标记中断（v2: 自动记录中断次数） |
| **fail** | `fail <FEATURE_ID> --blocked -m "<reason>"` | v2: 标记为外部阻塞 |

## ⚠️ 重要：log 命令特殊用法

`log` 命令会**自动关联**到当前运行中的会话，因此**不需要**指定功能ID：

```bash
# ✅ 正确
python3 .harness/feature_cli.py log "完成用户认证模块"

# ❌ 错误
python3 .harness/feature_cli.py log F001 "完成用户认证模块"
```

## 标准工作流示例

```bash
# 1. 查看下一个待开发功能
python3 .harness/feature_cli.py next

# 2. 开始开发
python3 .harness/feature_cli.py begin F025

# 3. 记录进度（可多次）
python3 .harness/feature_cli.py log "开始创建 FileUpload 组件"
python3 .harness/feature_cli.py log "完成文件上传逻辑"

# 4. 标记完成
python3 .harness/feature_cli.py complete F025 -m "文件上传功能完成"
```

## 常用查询命令

```bash
python3 .harness/feature_cli.py status      # 查看整体进度
python3 .harness/feature_cli.py list        # 列出所有功能
python3 .harness/feature_cli.py next        # 获取下一个功能
python3 .harness/feature_cli.py unblock     # 查看可开始的功能
python3 .harness/feature_cli.py report      # 生成进度报告
```

---

## dev.sh 子命令

### 开发流程

| 命令 | 说明 |
|------|------|
| `.harness/dev.sh plan` | 从需求生成功能清单 |
| `.harness/dev.sh migrate` | 从现有代码迁移 |
| `.harness/dev.sh run` | 自动循环开发 |
| `.harness/dev.sh status` | 查看进度 |

### 质量保证（新增）

| 命令 | 说明 |
|------|------|
| `.harness/dev.sh lint` | 代码规范检查 |
| `.harness/dev.sh lint --fix` | 自动修复问题 |
| `.harness/dev.sh garden` | 技术债扫描 |
| `.harness/dev.sh garden --auto` | 自动修复技术债 |
| `.harness/dev.sh doctor` | 项目健康检查 |

### 记忆系统

| 命令 | 说明 |
|------|------|
| `.harness/dev.sh remember "主题" "原因"` | 记录设计决策 |
| `.harness/dev.sh memory status` | 查看记忆状态 |
| `.harness/dev.sh memory export` | 导出项目知识（v2: 含失败反模式摘要） |

### v2 评测

| 命令 | 说明 |
|------|------|
| `python3 .harness/bench/eval.py run --tag v1` | 运行评测 |
| `python3 .harness/bench/eval.py compare v1 v2` | A/B 对比 |
| `python3 .harness/bench/eval.py list` | 历史评测 |

### v2 环境快照

| 命令 | 说明 |
|------|------|
| `python3 .harness/scripts/preflight.py --prompt` | 查看环境快照（dev.sh run 自动调用） |
| `python3 .harness/scripts/preflight.py --prompt --save` | 查看并保存到 logs/ |

