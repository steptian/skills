"""
学习式模板系统

用于收集团队运行指标并提取成功模板，支持 Agent Team 的持续优化。
"""

from .metrics import (
    MetricsCollector,
    TeamSessionMetrics,
    AgentMetrics,
    TaskMetrics,
    TaskStatus,
    QualityGateStatus,
)

from .template_extractor import (
    TemplateExtractor,
    SuccessCriteria,
    TeamTemplate,
    RoleTemplate,
)

from .exporter import (
    MarkdownExporter,
    JSONExporter,
)

__all__ = [
    # 指标收集
    "MetricsCollector",
    "TeamSessionMetrics",
    "AgentMetrics",
    "TaskMetrics",
    "TaskStatus",
    "QualityGateStatus",
    # 模板提取
    "TemplateExtractor",
    "SuccessCriteria",
    "TeamTemplate",
    "RoleTemplate",
    # 导出
    "MarkdownExporter",
    "JSONExporter",
]

__version__ = "1.0.0"
