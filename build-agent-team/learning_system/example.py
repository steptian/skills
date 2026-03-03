"""
学习式模板系统使用示例

演示如何使用指标收集、模板提取和导出功能。
"""

from pathlib import Path
import sys

# 添加 learning_system 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from metrics import (
    MetricsCollector,
    TeamSessionMetrics,
    QualityGateStatus,
)
from template_extractor import (
    TemplateExtractor,
    SuccessCriteria,
    TeamTemplate,
)
from exporter import (
    MarkdownExporter,
    JSONExporter,
)


def main():
    """运行示例"""

    # ========================================
    # 1. 指标收集
    # ========================================
    print("=" * 50)
    print("1. 开始收集团队指标...")
    print("=" * 50)

    collector = MetricsCollector()

    # 开始团队会话
    session = collector.start_session("fullstack-project-team")

    # 注册队友
    collector.register_agent(
        agent_name="frontend-dev",
        agent_type="前端工程师",
        owned_directories=["src/frontend/", "src/components/"],
        owned_files=["src/styles/common.css"],
    )

    collector.register_agent(
        agent_name="backend-dev",
        agent_type="后端工程师",
        owned_directories=["src/backend/", "src/api/"],
        owned_files=["src/config.py"],
    )

    collector.register_agent(
        agent_name="db-engineer",
        agent_type="数据库工程师",
        owned_directories=["src/database/", "migrations/"],
        owned_files=[],
    )

    collector.register_agent(
        agent_name="qa-engineer",
        agent_type="测试工程师",
        owned_directories=["tests/", "test-fixtures/"],
        owned_files=[],
    )

    print(f"   注册了 {len(session.agents)} 个队友")

    # 创建前端任务
    collector.create_task("task-001", "实现用户登录界面", "frontend-dev")
    collector.create_task("task-002", "实现用户注册表单", "frontend-dev")

    # 创建后端任务
    collector.create_task("task-003", "实现登录API接口", "backend-dev")
    collector.create_task("task-004", "实现用户注册API", "backend-dev")
    collector.create_task("task-005", "配置JWT认证", "backend-dev")

    # 创建数据库任务
    collector.create_task("task-006", "设计用户表结构", "db-engineer")
    collector.create_task("task-007", "创建数据库迁移脚本", "db-engineer", blocked_by=["task-006"])

    # 创建测试任务
    collector.create_task("task-008", "编写登录流程集成测试", "qa-engineer", blocked_by=["task-001", "task-003"])
    collector.create_task("task-009", "编写注册流程集成测试", "qa-engineer", blocked_by=["task-002", "task-004"])

    print(f"   创建了 {session.total_tasks} 个任务")

    # 模拟任务执行
    print("   执行任务中...")

    # 数据库任务先完成
    collector.start_task("task-006")
    collector.complete_task("task-006", {
        "schema_review": QualityGateStatus.PASSED,
    })

    collector.start_task("task-007")  # 依赖解除
    collector.complete_task("task-007", {
        "migration_test": QualityGateStatus.PASSED,
    })

    # 前端和后端并行
    collector.start_task("task-001")
    collector.start_task("task-002")
    collector.start_task("task-003")
    collector.start_task("task-004")
    collector.start_task("task-005")

    collector.complete_task("task-001", {
        "test_coverage": QualityGateStatus.PASSED,
        "lint_check": QualityGateStatus.PASSED,
    })
    collector.complete_task("task-002", {
        "test_coverage": QualityGateStatus.PASSED,
        "lint_check": QualityGateStatus.WARNING,  # 有警告但通过
    })
    collector.complete_task("task-003", {
        "test_coverage": QualityGateStatus.PASSED,
        "security_scan": QualityGateStatus.PASSED,
    })
    collector.complete_task("task-004", {
        "test_coverage": QualityGateStatus.PASSED,
        "security_scan": QualityGateStatus.PASSED,
    })
    collector.complete_task("task-005", {
        "security_review": QualityGateStatus.PASSED,
    })

    # 测试任务完成
    collector.start_task("task-008")
    collector.start_task("task-009")

    collector.complete_task("task-008", {
        "integration_test": QualityGateStatus.PASSED,
    })
    collector.complete_task("task-009", {
        "integration_test": QualityGateStatus.PASSED,
    })

    # 记录一些消息和冲突（少量冲突是允许的）
    collector.record_message("frontend-dev")
    collector.record_message("frontend-dev")
    collector.record_message("backend-dev")
    collector.record_conflict("frontend-dev")  # 1次冲突

    # 设置共享文件
    session.shared_files = ["src/shared/types.ts", "src/config.py"]

    # 结束会话
    session = collector.end_session()
    assert session is not None, "Session should not be None"

    print(f"   会话完成!")
    print()

    # ========================================
    # 2. 查看指标摘要
    # ========================================
    print("=" * 50)
    print("2. 指标摘要")
    print("=" * 50)

    summary = collector.get_session_summary()
    assert summary is not None, "Summary should not be None"
    print(f"   团队名称: {summary['team_name']}")
    summary_data = summary['summary']
    print(f"   总任务数: {summary_data['total_tasks']}")
    print(f"   已完成: {summary_data['completed_tasks']}")
    print(f"   完成率: {summary_data['completion_rate']:.0%}")
    print(f"   被阻塞任务: {summary_data['blocked_tasks']}")
    print(f"   阻塞比例: {summary_data['blocked_ratio']:.0%}")
    print(f"   质量门禁通过率: {summary_data['average_quality_pass_rate']:.0%}")
    print(f"   冲突次数: {summary_data['total_conflicts']}")
    print(f"   使用角色: {', '.join(summary['roles_used'])}")
    print()

    # ========================================
    # 3. 评估成功并提取模板
    # ========================================
    print("=" * 50)
    print("3. 评估成功标准并提取模板")
    print("=" * 50)

    # 创建提取器
    criteria = SuccessCriteria(
        min_quality_gate_pass_rate=0.90,
        max_conflict_count=3,
        min_completion_rate=1.0,
        max_blocked_ratio=0.2,
    )
    extractor = TemplateExtractor(criteria)

    # 评估是否成功
    is_successful, reasons = extractor.evaluate_success(session)
    print(f"   是否成功: {'是' if is_successful else '否'}")
    for reason in reasons:
        print(f"   - {reason}")
    print()

    # 提取模板
    template = extractor.extract_template(
        metrics=session,
        scenario="功能开发",
        template_name="全栈功能开发模板",
        tags=["全栈", "前后端分离", "测试驱动"],
    )

    if template:
        print(f"   模板已生成: {template.template_id}")
        print(f"   模板名称: {template.template_name}")
        print(f"   包含角色: {len(template.roles)} 个")
        for role in template.roles:
            print(f"      - {role.name}: 负责 {', '.join(role.owned_directories) or 'N/A'}")
    else:
        print("   未达到成功标准，未生成模板")
    print()

    # 获取最佳实践
    practices = extractor.get_best_practices(session)
    print("   最佳实践:")
    for pattern in practices.get("efficient_patterns", []):
        print(f"   - [效率] {pattern}")
    for rec in practices.get("ownership_recommendations", []):
        print(f"   - [所有权] {rec}")
    for synergy in practices.get("role_synergies", []):
        print(f"   - [协同] {synergy}")
    print()

    # ========================================
    # 4. 导出报告
    # ========================================
    print("=" * 50)
    print("4. 导出报告")
    print("=" * 50)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # 导出 Markdown 报告
    report_path = output_dir / "session_report.md"
    MarkdownExporter.export_session_report(session, report_path)
    print(f"   会话报告已保存: {report_path}")

    # 导出模板文档
    if template:
        template_path = output_dir / "team_template.md"
        MarkdownExporter.export_team_template(template, template_path)
        print(f"   模板文档已保存: {template_path}")

    # 导出 JSON 数据
    json_path = output_dir / "session_metrics.json"
    JSONExporter.export_session_metrics(session, json_path)
    print(f"   JSON 数据已保存: {json_path}")

    # 导出模板库索引
    if template:
        library_path = output_dir / "template_library.md"
        MarkdownExporter.export_template_library([template], library_path)
        print(f"   模板库索引已保存: {library_path}")

    print()
    print("示例完成!")


if __name__ == "__main__":
    main()
