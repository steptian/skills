# Agent Team 学习式模板系统

用于收集团队运行指标并提取成功模板的 Python 模块，支持 Agent Team 的持续优化和学习。

## 功能概述

- **指标收集**: 追踪团队运行过程中的效率、角色组合、所有权模式和任务粒度等指标
- **模板提取**: 当指标满足成功标准时，自动保存为可复用模板
- **格式导出**: 支持导出为 Markdown 和 JSON 格式

## 模块结构

```
learning_system/
├── __init__.py           # 模块入口
├── metrics.py            # 指标收集模块
├── template_extractor.py # 模板提取模块
├── exporter.py           # 导出模块
└── README.md             # 使用说明
```

## 快速开始

### 1. 指标收集

```python
from learning_system import MetricsCollector, QualityGateStatus

# 创建收集器
collector = MetricsCollector()

# 开始团队会话
session = collector.start_session("my-team")

# 注册队友
collector.register_agent(
    agent_name="frontend-dev",
    agent_type="前端工程师",
    owned_directories=["src/frontend/", "src/components/"],
)

collector.register_agent(
    agent_name="backend-dev",
    agent_type="后端工程师",
    owned_directories=["src/backend/", "src/api/"],
)

# 创建任务
collector.create_task(
    task_id="task-001",
    task_name="实现用户登录界面",
    owner="frontend-dev",
)

# 开始任务
collector.start_task("task-001")

# 完成任务（带质量门禁结果）
collector.complete_task(
    "task-001",
    quality_gate_results={
        "test_coverage": QualityGateStatus.PASSED,
        "lint_check": QualityGateStatus.PASSED,
    },
)

# 结束会话
session = collector.end_session()
```

### 2. 模板提取

```python
from learning_system import TemplateExtractor, SuccessCriteria

# 创建提取器（可自定义成功标准）
criteria = SuccessCriteria(
    min_quality_gate_pass_rate=0.90,  # 质量门禁通过率 > 90%
    max_conflict_count=3,             # 冲突次数 < 3
    min_completion_rate=1.0,          # 任务完成率 100%
    max_blocked_ratio=0.2,            # 被阻塞任务比例 < 20%
)
extractor = TemplateExtractor(criteria)

# 评估会话是否成功
is_successful, reasons = extractor.evaluate_success(session)
print(f"成功: {is_successful}")
for reason in reasons:
    print(f"  - {reason}")

# 提取模板（仅成功的会话会生成模板）
template = extractor.extract_template(
    metrics=session,
    scenario="功能开发",
    template_name="全栈开发模板",
    tags=["全栈", "前后端分离"],
)

if template:
    print(f"模板已生成: {template.template_id}")
```

### 3. 导出报告

```python
from learning_system import MarkdownExporter, JSONExporter
from pathlib import Path

# 导出会话报告（Markdown）
report = MarkdownExporter.export_session_report(
    metrics=session,
    output_path=Path("reports/session_report.md"),
)

# 导出模板（Markdown）
template_doc = MarkdownExporter.export_team_template(
    template=template,
    output_path=Path("templates/fullstack_template.md"),
)

# 导出指标数据（JSON）
data = JSONExporter.export_session_metrics(
    metrics=session,
    output_path=Path("data/session_metrics.json"),
)

# 导出模板库索引
MarkdownExporter.export_template_library(
    templates=[template],
    output_path=Path("templates/README.md"),
)
```

## 数据结构

### TeamSessionMetrics

团队会话的整体指标：

| 字段 | 类型 | 说明 |
|------|------|------|
| team_name | str | 团队名称 |
| created_at | datetime | 创建时间 |
| completed_at | datetime | 完成时间 |
| agents | list[AgentMetrics] | 队友列表 |
| total_conflicts | int | 冲突总数 |
| shared_files | list[str] | 共享文件列表 |

**计算属性**:
- `completion_rate`: 任务完成率
- `blocked_ratio`: 被阻塞任务比例
- `average_quality_pass_rate`: 平均质量门禁通过率

### AgentMetrics

单个队友的指标：

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_name | str | 队友名称 |
| agent_type | str | 队友类型/角色 |
| owned_directories | list[str] | 负责的目录 |
| owned_files | list[str] | 负责的文件 |
| tasks | list[TaskMetrics] | 任务列表 |
| conflicts_detected | int | 检测到的冲突数 |

### TaskMetrics

单个任务的指标：

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | str | 任务ID |
| task_name | str | 任务名称 |
| owner | str | 负责人 |
| status | TaskStatus | 任务状态 |
| quality_gate_results | dict | 质量门禁结果 |

### TeamTemplate

团队模板配置：

| 字段 | 类型 | 说明 |
|------|------|------|
| template_id | str | 模板ID |
| template_name | str | 模板名称 |
| scenario | str | 适用场景 |
| roles | list[RoleTemplate] | 角色列表 |
| ownership_map | dict | 所有权映射 |
| success_metrics | dict | 成功指标 |

## 成功标准

默认的成功标准配置：

```python
SuccessCriteria(
    min_quality_gate_pass_rate=0.90,  # 质量门禁通过率 > 90%
    max_conflict_count=3,             # 冲突次数 < 3
    min_completion_rate=1.0,          # 任务完成率 100%
    max_blocked_ratio=0.2,            # 被阻塞任务比例 < 20%
)
```

只有满足以上所有标准的团队会话才会被提取为可复用模板。

## 导出格式示例

### Markdown 会话报告

```markdown
# Agent Team 会话报告: my-team

## 会话概览
- **创建时间**: 2026-02-15 10:00:00
- **完成时间**: 2026-02-15 11:30:00
- **总耗时**: 90.0 分钟
- **团队成员数**: 4

## 任务统计
| 指标 | 数值 |
|------|------|
| 总任务数 | 12 |
| 已完成 | 12 |
| 完成率 | 100.0% |
| 质量门禁通过率 | 95.0% |
```

### Markdown 模板文档

```markdown
# Agent Team 模板: 全栈开发模板

> 模板ID: `template_my-team_20260215_103000`

## 基本信息
- **适用场景**: 功能开发
- **建议规模**: 4 人

## 角色定义

### 角色1: 前端工程师
**文件所有权**:
- `src/frontend/` (排他)
- `src/components/` (排他)
```

## 最佳实践提取

使用 `get_best_practices()` 方法可以从成功的团队会话中提取最佳实践：

```python
practices = extractor.get_best_practices(session)
# 返回:
# {
#     "efficient_patterns": ["任务粒度适中，平均完成时间短"],
#     "ownership_recommendations": ["src/frontend/ 由单一角色 frontend-dev 负责，减少冲突"],
#     "role_synergies": ["角色组合 前端工程师, 后端工程师, 测试工程师 协同无冲突"]
# }
```

## 与 SKILL.md 集成

本模块实现了 SKILL.md 第5节"学习式模板系统"的功能：

- **效率指标**: `average_task_completion_time`, `quality_gate_pass_rate`
- **角色组合**: `roles_used`, `conflict_count`
- **所有权模式**: `directory_structure`, `shared_files_handling`
- **任务粒度**: `tasks_per_agent`, `blocked_task_ratio`

提取的模板符合第4节"团队配置导出"的 Markdown 格式规范。

## 扩展开发

### 自定义成功标准

```python
class MySuccessCriteria(SuccessCriteria):
    def evaluate(self, metrics: TeamSessionMetrics) -> tuple[bool, list[str]]:
        # 添加自定义评估逻辑
        is_success, reasons = super().evaluate(metrics)
        # 例如：检查特定场景的额外条件
        return is_success, reasons
```

### 自定义导出格式

```python
class YAMLExporter:
    @staticmethod
    def export_template(template: TeamTemplate, output_path: Path) -> str:
        import yaml
        data = template.to_dict()
        with open(output_path, "w") as f:
            yaml.dump(data, f)
        return str(output_path)
```

## 许可证

MIT License
