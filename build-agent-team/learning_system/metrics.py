"""
团队运行指标收集模块

用于收集团队运行过程中的各类指标，包括效率、角色组合、所有权模式和任务粒度等。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class QualityGateStatus(Enum):
    """质量门禁状态枚举"""
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


@dataclass
class TaskMetrics:
    """单个任务的指标数据"""
    task_id: str
    task_name: str
    owner: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    blocked_by: list[str] = field(default_factory=list)
    quality_gate_results: dict[str, QualityGateStatus] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """计算任务耗时（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_blocked(self) -> bool:
        """判断任务是否当前被阻塞（状态为 BLOCKED）"""
        return self.status == TaskStatus.BLOCKED

    @property
    def has_dependencies(self) -> bool:
        """判断任务是否有依赖关系"""
        return len(self.blocked_by) > 0

    @property
    def quality_gate_pass_rate(self) -> float:
        """计算质量门禁通过率"""
        if not self.quality_gate_results:
            return 1.0  # 没有质量门禁要求时默认通过
        passed = sum(1 for s in self.quality_gate_results.values() if s == QualityGateStatus.PASSED)
        return passed / len(self.quality_gate_results)


@dataclass
class AgentMetrics:
    """单个队友的指标数据"""
    agent_name: str
    agent_type: str
    owned_directories: list[str] = field(default_factory=list)
    owned_files: list[str] = field(default_factory=list)
    tasks: list[TaskMetrics] = field(default_factory=list)
    messages_sent: int = 0
    conflicts_detected: int = 0

    @property
    def completed_tasks_count(self) -> int:
        """已完成任务数量"""
        return sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)

    @property
    def blocked_tasks_count(self) -> int:
        """被阻塞任务数量"""
        return sum(1 for t in self.tasks if t.is_blocked)

    @property
    def average_task_duration(self) -> Optional[float]:
        """平均任务耗时（秒）"""
        durations = [t.duration_seconds for t in self.tasks if t.duration_seconds is not None]
        if durations:
            return sum(durations) / len(durations)
        return None

    @property
    def average_quality_pass_rate(self) -> float:
        """平均质量门禁通过率"""
        rates = [t.quality_gate_pass_rate for t in self.tasks if t.status == TaskStatus.COMPLETED]
        if rates:
            return sum(rates) / len(rates)
        return 1.0


@dataclass
class TeamSessionMetrics:
    """团队会话的整体指标"""
    team_name: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    agents: list[AgentMetrics] = field(default_factory=list)
    total_conflicts: int = 0
    shared_files: list[str] = field(default_factory=list)

    @property
    def total_tasks(self) -> int:
        """总任务数"""
        return sum(len(a.tasks) for a in self.agents)

    @property
    def completed_tasks(self) -> int:
        """已完成任务数"""
        return sum(a.completed_tasks_count for a in self.agents)

    @property
    def blocked_tasks(self) -> int:
        """被阻塞任务数"""
        return sum(a.blocked_tasks_count for a in self.agents)

    @property
    def completion_rate(self) -> float:
        """任务完成率"""
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    @property
    def blocked_ratio(self) -> float:
        """被阻塞任务比例"""
        if self.total_tasks == 0:
            return 0.0
        return self.blocked_tasks / self.total_tasks

    @property
    def average_quality_pass_rate(self) -> float:
        """团队整体质量门禁通过率"""
        rates = [a.average_quality_pass_rate for a in self.agents]
        if rates:
            return sum(rates) / len(rates)
        return 1.0

    @property
    def average_task_duration(self) -> Optional[float]:
        """团队平均任务耗时（秒）"""
        durations = [a.average_task_duration for a in self.agents if a.average_task_duration is not None]
        if durations:
            return sum(durations) / len(durations)
        return None

    @property
    def duration_seconds(self) -> Optional[float]:
        """团队会话总耗时（秒）"""
        if self.created_at and self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return None

    def get_roles_used(self) -> list[str]:
        """获取使用的角色列表"""
        return [a.agent_type for a in self.agents]

    def get_ownership_map(self) -> dict[str, list[str]]:
        """获取目录所有权映射"""
        ownership = {}
        for agent in self.agents:
            for directory in agent.owned_directories:
                if directory not in ownership:
                    ownership[directory] = []
                ownership[directory].append(agent.agent_name)
        return ownership

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "team_name": self.team_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "summary": {
                "total_tasks": self.total_tasks,
                "completed_tasks": self.completed_tasks,
                "blocked_tasks": self.blocked_tasks,
                "completion_rate": round(self.completion_rate, 2),
                "blocked_ratio": round(self.blocked_ratio, 2),
                "average_quality_pass_rate": round(self.average_quality_pass_rate, 2),
                "average_task_duration": self.average_task_duration,
                "total_duration_seconds": self.duration_seconds,
                "total_conflicts": self.total_conflicts,
            },
            "roles_used": self.get_roles_used(),
            "ownership_map": self.get_ownership_map(),
            "shared_files": self.shared_files,
            "agents": [
                {
                    "name": a.agent_name,
                    "type": a.agent_type,
                    "tasks_count": len(a.tasks),
                    "completed_tasks": a.completed_tasks_count,
                    "blocked_tasks": a.blocked_tasks_count,
                    "average_quality_pass_rate": round(a.average_quality_pass_rate, 2),
                    "conflicts_detected": a.conflicts_detected,
                }
                for a in self.agents
            ],
        }


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.current_session: Optional[TeamSessionMetrics] = None
        self.task_map: dict[str, TaskMetrics] = {}
        self.agent_map: dict[str, AgentMetrics] = {}

    def start_session(self, team_name: str) -> TeamSessionMetrics:
        """开始新的团队会话"""
        self.current_session = TeamSessionMetrics(
            team_name=team_name,
            created_at=datetime.now(),
        )
        self.task_map.clear()
        self.agent_map.clear()
        return self.current_session

    def register_agent(
        self,
        agent_name: str,
        agent_type: str,
        owned_directories: Optional[list[str]] = None,
        owned_files: Optional[list[str]] = None,
    ) -> AgentMetrics:
        """注册队友"""
        if not self.current_session:
            raise RuntimeError("No active session. Call start_session first.")

        agent = AgentMetrics(
            agent_name=agent_name,
            agent_type=agent_type,
            owned_directories=owned_directories or [],
            owned_files=owned_files or [],
        )
        self.agent_map[agent_name] = agent
        self.current_session.agents.append(agent)
        return agent

    def create_task(
        self,
        task_id: str,
        task_name: str,
        owner: str,
        blocked_by: Optional[list[str]] = None,
    ) -> TaskMetrics:
        """创建任务"""
        if not self.current_session:
            raise RuntimeError("No active session. Call start_session first.")

        if owner not in self.agent_map:
            raise ValueError(f"Agent '{owner}' not registered.")

        task = TaskMetrics(
            task_id=task_id,
            task_name=task_name,
            owner=owner,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            blocked_by=blocked_by or [],
        )
        self.task_map[task_id] = task
        self.agent_map[owner].tasks.append(task)
        return task

    def start_task(self, task_id: str) -> Optional[TaskMetrics]:
        """开始任务"""
        if task_id not in self.task_map:
            return None
        task = self.task_map[task_id]
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        return task

    def complete_task(
        self,
        task_id: str,
        quality_gate_results: Optional[dict[str, QualityGateStatus]] = None,
    ) -> Optional[TaskMetrics]:
        """完成任务"""
        if task_id not in self.task_map:
            return None
        task = self.task_map[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        if quality_gate_results:
            task.quality_gate_results = quality_gate_results
        return task

    def block_task(self, task_id: str, blocked_by: list[str]) -> Optional[TaskMetrics]:
        """阻塞任务"""
        if task_id not in self.task_map:
            return None
        task = self.task_map[task_id]
        task.status = TaskStatus.BLOCKED
        task.blocked_by = blocked_by
        return task

    def fail_task(self, task_id: str) -> Optional[TaskMetrics]:
        """标记任务失败"""
        if task_id not in self.task_map:
            return None
        task = self.task_map[task_id]
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now()
        return task

    def record_conflict(self, agent_name: str) -> None:
        """记录冲突"""
        if agent_name in self.agent_map:
            self.agent_map[agent_name].conflicts_detected += 1
        if self.current_session:
            self.current_session.total_conflicts += 1

    def record_message(self, agent_name: str) -> None:
        """记录消息发送"""
        if agent_name in self.agent_map:
            self.agent_map[agent_name].messages_sent += 1

    def end_session(self) -> Optional[TeamSessionMetrics]:
        """结束团队会话"""
        if not self.current_session:
            return None
        self.current_session.completed_at = datetime.now()
        return self.current_session

    def get_session_summary(self) -> Optional[dict]:
        """获取会话摘要"""
        if not self.current_session:
            return None
        return self.current_session.to_dict()
