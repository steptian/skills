#!/usr/bin/env python3
"""
BOSS 直聘招聘助手 - 会话管理器
用于保存和恢复处理进度，支持断点续传
"""

import json
from pathlib import Path
from datetime import datetime
import uuid

# 会话文件路径
SESSION_PATH = Path.home() / ".claude/projects/-Users-steptian-Documents-iLike-Python-feilian-skills/memory/boss-recruiter"
SESSION_FILE = SESSION_PATH / "session.json"

# 检查点间隔（分钟）
CHECKPOINT_INTERVAL_MINUTES = 10


def create_session(phase: str = "init") -> dict:
    """创建新会话"""
    session_id = datetime.now().strftime("%Y-%m-%d-%H-%M") + "-" + str(uuid.uuid4())[:8]

    session = {
        "session_id": session_id,
        "start_time": datetime.now().isoformat(),
        "last_checkpoint": datetime.now().isoformat(),
        "elapsed_minutes": 0,
        "phase": phase,  # "init", "unread", "recommend", "done"
        "current_target": "",
        "processed": [],
        "pending": [],
        "stats": {
            "unread_processed": 0,
            "new_contacts": 0,
            "resumes_requested": 0,
            "errors": 0
        }
    }

    save_session(session)
    return session


def save_session(session: dict) -> None:
    """保存会话到文件"""
    SESSION_PATH.mkdir(parents=True, exist_ok=True)
    session["last_checkpoint"] = datetime.now().isoformat()

    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(session, f, ensure_ascii=False, indent=2)


def load_session() -> dict | None:
    """加载会话"""
    if not SESSION_FILE.exists():
        return None

    with open(SESSION_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def should_checkpoint(session: dict) -> bool:
    """检查是否需要触发检查点"""
    start = datetime.fromisoformat(session["start_time"])
    elapsed = (datetime.now() - start).total_seconds() / 60
    return elapsed >= CHECKPOINT_INTERVAL_MINUTES


def get_elapsed_minutes(session: dict) -> int:
    """获取已用时间（分钟）"""
    start = datetime.fromisoformat(session["start_time"])
    return int((datetime.now() - start).total_seconds() / 60)


def reset_timer(session: dict) -> dict:
    """重置计时器（恢复后使用）"""
    session["start_time"] = datetime.now().isoformat()
    session["elapsed_minutes"] = 0
    return session


def add_processed(session: dict, candidate: dict) -> dict:
    """添加已处理的候选人"""
    candidate["processed_at"] = datetime.now().isoformat()
    session["processed"].append(candidate)
    return session


def add_pending(session: dict, candidate: dict) -> dict:
    """添加待处理的候选人"""
    session["pending"].append(candidate)
    return session


def get_next_pending(session: dict) -> dict | None:
    """获取下一个待处理的候选人"""
    if session["pending"]:
        return session["pending"].pop(0)
    return None


def update_stats(session: dict, key: str, delta: int = 1) -> dict:
    """更新统计数据"""
    if key in session["stats"]:
        session["stats"][key] += delta
    return session


def generate_checkpoint_message(session: dict) -> str:
    """生成检查点消息"""
    elapsed = get_elapsed_minutes(session)

    message = f"""
⏰ 已工作 {elapsed} 分钟，建议重置上下文以保持性能。

📊 当前进度：
- 当前阶段：{session['phase']}
- 已处理：{len(session['processed'])} 位候选人
- 待处理：{len(session['pending'])} 位候选人
- 简历获取：{session['stats']['resumes_requested']} 份
- 新增联系：{session['stats']['new_contacts']} 人

💾 进度已保存到 session.json

请说"继续"来恢复工作，或说"结束"保存并退出。
"""
    return message.strip()


def generate_restore_message(session: dict) -> str:
    """生成恢复消息"""
    message = f"""
📂 从检查点恢复：
- 恢复时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
- 当前阶段：{session['phase']}
- 已处理：{len(session['processed'])} 位候选人
- 待处理：{len(session['pending'])} 位候选人

继续处理...
"""
    return message.strip()


def clear_session() -> None:
    """清除会话文件"""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


# CLI 接口
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python session_manager.py <command> [args]")
        print("命令:")
        print("  create <phase>     - 创建新会话")
        print("  status             - 查看会话状态")
        print("  checkpoint         - 检查是否需要检查点")
        print("  clear              - 清除会话")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        phase = sys.argv[2] if len(sys.argv) > 2 else "init"
        session = create_session(phase)
        print(f"✅ 会话已创建: {session['session_id']}")

    elif command == "status":
        session = load_session()
        if session:
            elapsed = get_elapsed_minutes(session)
            print(f"📊 会话状态:")
            print(f"   ID: {session['session_id']}")
            print(f"   阶段: {session['phase']}")
            print(f"   已用时: {elapsed} 分钟")
            print(f"   已处理: {len(session['processed'])} 人")
            print(f"   待处理: {len(session['pending'])} 人")
        else:
            print("❌ 没有活跃的会话")

    elif command == "checkpoint":
        session = load_session()
        if session and should_checkpoint(session):
            print(generate_checkpoint_message(session))
        else:
            elapsed = get_elapsed_minutes(session) if session else 0
            print(f"⏱️ 已工作 {elapsed} 分钟，无需检查点")

    elif command == "clear":
        clear_session()
        print("🗑️ 会话已清除")
