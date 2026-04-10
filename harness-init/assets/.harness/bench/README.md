# Harness Bench — 评测闭环

在每次修改 prompt 或流程后，用固定任务集跑 A/B 对比，量化改进效果。

## 目录结构

```
bench/
├── tasks/          # 基准任务定义（JSON）
├── results/        # 每次评测运行的结果
├── eval.py         # 评测对比脚本
└── README.md       # 本文件
```

## 任务定义格式

每个 `tasks/*.json` 文件代表一个基准任务：

```json
{
  "id": "T001",
  "name": "创建 Python CLI 工具",
  "category": "feature",
  "difficulty": "easy|medium|hard",
  "description": "任务描述（会传给 agent）",
  "acceptance_check": "验收检查命令（exit 0 = 通过）",
  "expected_files": ["main.py", "requirements.txt"],
  "max_turns": 20,
  "tags": ["python", "cli"]
}
```

## 评测流程

```bash
# 1. 运行评测（A 版本）
python3 .harness/bench/eval.py run --tag v1 --tasks tasks/

# 2. 修改 prompt/流程

# 3. 运行评测（B 版本）
python3 .harness/bench/eval.py run --tag v2 --tasks tasks/

# 4. 对比结果
python3 .harness/bench/eval.py compare v1 v2
```

## 关键指标

| 指标 | 说明 |
|------|------|
| `success_rate` | 任务成功率 |
| `avg_turns` | 平均轮次 |
| `avg_duration_min` | 平均耗时（分钟） |
| `empty_session_rate` | 空会话率（无有效日志） |
| `regression_count` | 相比基线退化的任务数 |
