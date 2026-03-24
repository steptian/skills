#!/usr/bin/env python3
"""
初始化 BOSS 直聘招聘助手的历史记录文件
"""

import json
from pathlib import Path
from datetime import datetime

# 历史记录路径
HISTORY_PATH = Path.home() / ".claude/projects/-Users-steptian-Documents-iLike-Python-feilian-skills/memory/boss-recruiter"
HISTORY_FILE = HISTORY_PATH / "history.json"

def init_history():
    """初始化历史记录文件"""
    # 确保目录存在
    HISTORY_PATH.mkdir(parents=True, exist_ok=True)

    # 如果文件不存在，创建空记录
    if not HISTORY_FILE.exists():
        initial_data = {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "sessions": [],
            "statistics": {
                "total_sessions": 0,
                "total_candidates_processed": 0,
                "total_resumes_requested": 0,
                "total_new_contacts": 0
            }
        }

        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 历史记录文件已创建: {HISTORY_FILE}")
        return initial_data
    else:
        # 读取现有文件
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"📁 历史记录文件已存在: {HISTORY_FILE}")
        print(f"   已记录 {data['statistics']['total_sessions']} 个会话")
        print(f"   已处理 {data['statistics']['total_candidates_processed']} 位候选人")

        return data

def get_history():
    """获取历史记录"""
    if not HISTORY_FILE.exists():
        return init_history()

    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def add_session(session_data):
    """添加新的会话记录"""
    data = get_history()

    # 添加新会话
    data['sessions'].append(session_data)
    data['last_updated'] = datetime.now().isoformat()

    # 更新统计
    data['statistics']['total_sessions'] += 1
    data['statistics']['total_candidates_processed'] += session_data['summary']['unread_processed'] + session_data['summary']['new_contacts']
    data['statistics']['total_resumes_requested'] += session_data['summary']['resumes_requested']
    data['statistics']['total_new_contacts'] += session_data['summary']['new_contacts']

    # 保存
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data

if __name__ == "__main__":
    init_history()
