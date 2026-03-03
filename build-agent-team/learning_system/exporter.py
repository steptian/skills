"""
导出模块

支持将团队指标和模板导出为 Markdown 格式。
"""

from datetime import datetime
from typing import Optional
from pathlib import Path

try:
    from .metrics import TeamSessionMetrics, TaskStatus
    from .template_extractor import TeamTemplate
except ImportError:
    from metrics import TeamSessionMetrics, TaskStatus
    from template_extractor import TeamTemplate


class MarkdownExporter:
    """Markdown 格式导出器"""

    @staticmethod
    def export_session_report(
        metrics: TeamSessionMetrics,
        output_path: Optional[Path] = None,
    ) -> str:
        """
        导出团队会话报告为 Markdown 格式
        """
        lines = []

        # 标题
        lines.append(f"# Agent Team 会话报告: {metrics.team_name}")
        lines.append("")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 概览
        lines.append("## 会话概览")
        lines.append("")
        lines.append(f"- **创建时间**: {metrics.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if metrics.completed_at:
            lines.append(f"- **完成时间**: {metrics.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if metrics.duration_seconds:
                duration_min = metrics.duration_seconds / 60
                lines.append(f"- **总耗时**: {duration_min:.1f} 分钟")
        lines.append(f"- **团队成员数**: {len(metrics.agents)}")
        lines.append("")

        # 任务统计
        lines.append("## 任务统计")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 总任务数 | {metrics.total_tasks} |")
        lines.append(f"| 已完成 | {metrics.completed_tasks} |")
        lines.append(f"| 被阻塞 | {metrics.blocked_tasks} |")
        lines.append(f"| 完成率 | {metrics.completion_rate:.1%} |")
        lines.append(f"| 阻塞比例 | {metrics.blocked_ratio:.1%} |")
        lines.append(f"| 质量门禁通过率 | {metrics.average_quality_pass_rate:.1%} |")
        lines.append(f"| 冲突次数 | {metrics.total_conflicts} |")
        lines.append("")

        # 角色列表
        lines.append("## 角色配置")
        lines.append("")
        roles = metrics.get_roles_used()
        lines.append(f"使用的角色: {', '.join(roles)}")
        lines.append("")

        # 所有权映射
        lines.append("## 文件所有权映射")
        lines.append("")
        ownership_map = metrics.get_ownership_map()
        if ownership_map:
            lines.append(f"| 目录 | 负责角色 |")
            lines.append(f"|------|---------|")
            for directory, owners in ownership_map.items():
                lines.append(f"| `{directory}` | {', '.join(owners)} |")
        else:
            lines.append("*暂无所有权映射*")
        lines.append("")

        # 队友详情
        lines.append("## 队友详情")
        lines.append("")
        for agent in metrics.agents:
            lines.append(f"### {agent.agent_name} ({agent.agent_type})")
            lines.append("")
            lines.append(f"- **负责目录**: {', '.join(agent.owned_directories) or '无'}")
            lines.append(f"- **任务数**: {len(agent.tasks)} (已完成: {agent.completed_tasks_count}, 被阻塞: {agent.blocked_tasks_count})")
            lines.append(f"- **质量门禁通过率**: {agent.average_quality_pass_rate:.1%}")
            lines.append(f"- **发送消息数**: {agent.messages_sent}")
            lines.append(f"- **检测到的冲突**: {agent.conflicts_detected}")
            if agent.average_task_duration:
                lines.append(f"- **平均任务耗时**: {agent.average_task_duration:.1f} 秒")
            lines.append("")

            # 任务列表
            if agent.tasks:
                lines.append("**任务列表:**")
                lines.append("")
                for task in agent.tasks:
                    status_emoji = {
                        TaskStatus.PENDING: "⏳",
                        TaskStatus.IN_PROGRESS: "🔄",
                        TaskStatus.COMPLETED: "✅",
                        TaskStatus.BLOCKED: "🚫",
                        TaskStatus.FAILED: "❌",
                    }.get(task.status, "❓")
                    lines.append(f"- {status_emoji} `{task.task_id}`: {task.task_name}")
                    if task.blocked_by:
                        lines.append(f"  - 被阻塞: {', '.join(task.blocked_by)}")
                lines.append("")

        # 共享文件
        if metrics.shared_files:
            lines.append("## 共享文件")
            lines.append("")
            for f in metrics.shared_files:
                lines.append(f"- `{f}`")
            lines.append("")

        content = "\n".join(lines)

        # 保存到文件
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

        return content

    @staticmethod
    def export_team_template(
        template: TeamTemplate,
        output_path: Optional[Path] = None,
    ) -> str:
        """
        导出团队模板为 Markdown 格式
        """
        lines = []

        # 标题
        lines.append(f"# Agent Team 模板: {template.template_name}")
        lines.append("")
        lines.append(f"> 模板ID: `{template.template_id}`")
        lines.append(f"> 创建时间: {template.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 来源团队: {template.source_team_name}")
        lines.append("")

        # 基本信息
        lines.append("## 基本信息")
        lines.append("")
        lines.append(f"- **适用场景**: {template.scenario}")
        lines.append(f"- **建议规模**: {template.recommended_team_size} 人")
        lines.append(f"- **标签**: {', '.join(template.tags)}")
        lines.append("")

        # 角色定义
        lines.append("## 角色定义")
        lines.append("")
        for i, role in enumerate(template.roles, 1):
            lines.append(f"### 角色{i}: {role.name}")
            lines.append("")
            lines.append(f"**职责**: {role.description}")
            lines.append("")

            if role.owned_directories:
                lines.append("**文件所有权**:")
                lines.append("")
                for d in role.owned_directories:
                    lines.append(f"- `{d}` (排他)")
                lines.append("")

            if role.typical_tasks:
                lines.append("**典型任务**:")
                lines.append("")
                for t in role.typical_tasks:
                    lines.append(f"- {t}")
                lines.append("")

            if role.quality_requirements:
                lines.append("**质量要求**:")
                lines.append("")
                for q in role.quality_requirements:
                    lines.append(f"- [ ] {q}")
                lines.append("")

        # 文件所有权映射
        lines.append("## 文件所有权映射")
        lines.append("")
        if template.ownership_map:
            lines.append(f"| 目录 | 负责角色 |")
            lines.append(f"|------|---------|")
            for directory, role in template.ownership_map.items():
                lines.append(f"| `{directory}` | {role} |")
        else:
            lines.append("*暂无所有权映射*")
        lines.append("")

        # 共享文件模式
        if template.shared_files_pattern:
            lines.append("## 共享文件处理模式")
            lines.append("")
            for pattern in template.shared_files_pattern:
                lines.append(f"- `{pattern}`")
            lines.append("")

        # 成功指标
        lines.append("## 成功指标（来源项目）")
        lines.append("")
        if template.success_metrics:
            lines.append(f"| 指标 | 数值 |")
            lines.append(f"|------|------|")
            for key, value in template.success_metrics.items():
                if isinstance(value, float):
                    lines.append(f"| {key} | {value:.2f} |")
                else:
                    lines.append(f"| {key} | {value} |")
        else:
            lines.append("*暂无成功指标*")
        lines.append("")

        # 使用说明
        lines.append("## 使用说明")
        lines.append("")
        lines.append("```")
        lines.append(f"/build-agent-team 使用模板 {template.template_name}")
        lines.append("```")
        lines.append("")

        content = "\n".join(lines)

        # 保存到文件
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

        return content

    @staticmethod
    def export_template_library(
        templates: list[TeamTemplate],
        output_path: Optional[Path] = None,
    ) -> str:
        """
        导出模板库索引为 Markdown 格式
        """
        lines = []

        lines.append("# Agent Team 模板库")
        lines.append("")
        lines.append(f"> 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 模板数量: {len(templates)}")
        lines.append("")

        if not templates:
            lines.append("*暂无可用模板*")
        else:
            lines.append("## 可用模板")
            lines.append("")
            lines.append(f"| 模板名称 | 适用场景 | 建议规模 | 标签 |")
            lines.append(f"|----------|----------|----------|------|")
            for template in templates:
                tags_str = ", ".join(template.tags) if template.tags else "-"
                lines.append(
                    f"| {template.template_name} | {template.scenario} | "
                    f"{template.recommended_team_size}人 | {tags_str} |"
                )
            lines.append("")

            # 详细列表
            for template in templates:
                lines.append(f"### {template.template_name}")
                lines.append("")
                lines.append(f"- **模板ID**: `{template.template_id}`")
                lines.append(f"- **创建时间**: {template.created_at.strftime('%Y-%m-%d')}")
                lines.append(f"- **角色数量**: {len(template.roles)}")
                roles_str = ", ".join(r.name for r in template.roles)
                lines.append(f"- **包含角色**: {roles_str}")
                lines.append("")

        content = "\n".join(lines)

        # 保存到文件
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

        return content


class JSONExporter:
    """JSON 格式导出器"""

    @staticmethod
    def export_session_metrics(
        metrics: TeamSessionMetrics,
        output_path: Optional[Path] = None,
    ) -> dict:
        """导出团队指标为JSON格式"""
        import json

        data = metrics.to_dict()

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return data
