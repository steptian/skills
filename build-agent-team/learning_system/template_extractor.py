"""
模板提取模块

从成功的团队会话中提取可复用的模板配置。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json
from pathlib import Path

try:
    from .metrics import (
        TeamSessionMetrics,
        TaskStatus,
        QualityGateStatus,
    )
except ImportError:
    from metrics import (
        TeamSessionMetrics,
        TaskStatus,
        QualityGateStatus,
    )


@dataclass
class SuccessCriteria:
    """成功标准配置"""
    min_quality_gate_pass_rate: float = 0.90  # 质量门禁通过率 > 90%
    max_conflict_count: int = 3  # 冲突次数 < 3
    min_completion_rate: float = 1.0  # 任务完成率 100%
    max_blocked_ratio: float = 0.2  # 被阻塞任务比例 < 20%


@dataclass
class RoleTemplate:
    """角色模板"""
    name: str
    description: str
    owned_directories: list[str] = field(default_factory=list)
    owned_files: list[str] = field(default_factory=list)
    typical_tasks: list[str] = field(default_factory=list)
    quality_requirements: list[str] = field(default_factory=list)


@dataclass
class TeamTemplate:
    """团队模板"""
    template_id: str
    template_name: str
    created_at: datetime
    source_team_name: str
    scenario: str  # 功能开发 | 代码评审 | 调试 | 架构设计
    roles: list[RoleTemplate] = field(default_factory=list)
    ownership_map: dict[str, str] = field(default_factory=dict)  # 目录 -> 角色名
    shared_files_pattern: list[str] = field(default_factory=list)
    recommended_team_size: int = 4
    success_metrics: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "created_at": self.created_at.isoformat(),
            "source_team_name": self.source_team_name,
            "scenario": self.scenario,
            "recommended_team_size": self.recommended_team_size,
            "roles": [
                {
                    "name": r.name,
                    "description": r.description,
                    "owned_directories": r.owned_directories,
                    "owned_files": r.owned_files,
                    "typical_tasks": r.typical_tasks,
                    "quality_requirements": r.quality_requirements,
                }
                for r in self.roles
            ],
            "ownership_map": self.ownership_map,
            "shared_files_pattern": self.shared_files_pattern,
            "success_metrics": self.success_metrics,
            "tags": self.tags,
        }


class TemplateExtractor:
    """模板提取器"""

    def __init__(self, success_criteria: Optional[SuccessCriteria] = None):
        self.success_criteria = success_criteria or SuccessCriteria()
        self.extracted_templates: list[TeamTemplate] = []

    def evaluate_success(self, metrics: TeamSessionMetrics) -> tuple[bool, list[str]]:
        """
        评估团队会话是否满足成功标准

        返回: (是否成功, 原因列表)
        """
        reasons = []
        is_successful = True

        # 检查质量门禁通过率
        if metrics.average_quality_pass_rate < self.success_criteria.min_quality_gate_pass_rate:
            is_successful = False
            reasons.append(
                f"质量门禁通过率 {metrics.average_quality_pass_rate:.1%} "
                f"低于要求 {self.success_criteria.min_quality_gate_pass_rate:.1%}"
            )
        else:
            reasons.append(
                f"质量门禁通过率 {metrics.average_quality_pass_rate:.1%} 达标"
            )

        # 检查冲突次数
        if metrics.total_conflicts > self.success_criteria.max_conflict_count:
            is_successful = False
            reasons.append(
                f"冲突次数 {metrics.total_conflicts} "
                f"超过上限 {self.success_criteria.max_conflict_count}"
            )
        else:
            reasons.append(
                f"冲突次数 {metrics.total_conflicts} 在允许范围内"
            )

        # 检查任务完成率
        if metrics.completion_rate < self.success_criteria.min_completion_rate:
            is_successful = False
            reasons.append(
                f"任务完成率 {metrics.completion_rate:.1%} "
                f"低于要求 {self.success_criteria.min_completion_rate:.1%}"
            )
        else:
            reasons.append(
                f"任务完成率 {metrics.completion_rate:.1%} 达标"
            )

        # 检查被阻塞任务比例
        if metrics.blocked_ratio > self.success_criteria.max_blocked_ratio:
            is_successful = False
            reasons.append(
                f"被阻塞任务比例 {metrics.blocked_ratio:.1%} "
                f"超过上限 {self.success_criteria.max_blocked_ratio:.1%}"
            )
        else:
            reasons.append(
                f"被阻塞任务比例 {metrics.blocked_ratio:.1%} 在允许范围内"
            )

        return is_successful, reasons

    def extract_template(
        self,
        metrics: TeamSessionMetrics,
        scenario: str,
        template_name: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[TeamTemplate]:
        """
        从团队指标中提取模板

        只有满足成功标准的会话才会生成模板
        """
        is_successful, _ = self.evaluate_success(metrics)

        if not is_successful:
            return None

        # 生成模板ID
        template_id = f"template_{metrics.team_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 提取角色模板
        roles = []
        ownership_map = {}

        for agent in metrics.agents:
            # 从完成的任务中提取典型任务描述
            typical_tasks = [
                t.task_name for t in agent.tasks
                if t.status == TaskStatus.COMPLETED
            ][:5]  # 最多取5个典型任务

            # 从质量门禁结果中提取质量要求
            quality_requirements = []
            for task in agent.tasks:
                if task.status == TaskStatus.COMPLETED:
                    for gate, status in task.quality_gate_results.items():
                        if status == QualityGateStatus.PASSED and gate not in quality_requirements:
                            quality_requirements.append(gate)

            role = RoleTemplate(
                name=agent.agent_type,
                description=f"{agent.agent_type} 角色，负责 {', '.join(agent.owned_directories) or '相关任务'}",
                owned_directories=agent.owned_directories.copy(),
                owned_files=agent.owned_files.copy(),
                typical_tasks=typical_tasks,
                quality_requirements=quality_requirements,
            )
            roles.append(role)

            # 建立所有权映射
            for directory in agent.owned_directories:
                ownership_map[directory] = agent.agent_type

        # 创建团队模板
        template = TeamTemplate(
            template_id=template_id,
            template_name=template_name or f"{scenario}模板-{metrics.team_name}",
            created_at=datetime.now(),
            source_team_name=metrics.team_name,
            scenario=scenario,
            roles=roles,
            ownership_map=ownership_map,
            shared_files_pattern=metrics.shared_files,
            recommended_team_size=len(metrics.agents),
            success_metrics=metrics.to_dict()["summary"],
            tags=tags or [scenario],
        )

        self.extracted_templates.append(template)
        return template

    def get_best_practices(self, metrics: TeamSessionMetrics) -> dict:
        """
        从团队指标中提取最佳实践
        """
        practices = {
            "efficient_patterns": [],
            "ownership_recommendations": [],
            "role_synergies": [],
        }

        # 分析高效模式
        if metrics.average_task_duration and metrics.average_task_duration < 300:  # 5分钟内
            practices["efficient_patterns"].append(
                "任务粒度适中，平均完成时间短"
            )

        if metrics.blocked_ratio < 0.1:  # 低于10%阻塞率
            practices["efficient_patterns"].append(
                "任务依赖管理良好，阻塞率极低"
            )

        # 分析所有权模式
        ownership_map = metrics.get_ownership_map()
        for directory, owners in ownership_map.items():
            if len(owners) == 1:
                practices["ownership_recommendations"].append(
                    f"{directory} 由单一角色 {owners[0]} 负责，减少冲突"
                )

        # 分析角色协同
        roles = metrics.get_roles_used()
        if len(roles) >= 3 and metrics.total_conflicts == 0:
            practices["role_synergies"].append(
                f"角色组合 {', '.join(roles)} 协同无冲突"
            )

        return practices

    def save_template(self, template: TeamTemplate, output_dir: Path) -> Path:
        """保存模板到JSON文件"""
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{template.template_id}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)

        return output_path

    def load_template(self, template_path: Path) -> TeamTemplate:
        """从JSON文件加载模板"""
        with open(template_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        roles = [
            RoleTemplate(
                name=r["name"],
                description=r["description"],
                owned_directories=r.get("owned_directories", []),
                owned_files=r.get("owned_files", []),
                typical_tasks=r.get("typical_tasks", []),
                quality_requirements=r.get("quality_requirements", []),
            )
            for r in data.get("roles", [])
        ]

        return TeamTemplate(
            template_id=data["template_id"],
            template_name=data["template_name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            source_team_name=data["source_team_name"],
            scenario=data["scenario"],
            roles=roles,
            ownership_map=data.get("ownership_map", {}),
            shared_files_pattern=data.get("shared_files_pattern", []),
            recommended_team_size=data.get("recommended_team_size", 4),
            success_metrics=data.get("success_metrics", {}),
            tags=data.get("tags", []),
        )
