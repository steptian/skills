"""
失败反模式自动归类模块
"""

import json
from datetime import datetime
from pathlib import Path

from .core import MEMORY_DIR

ANTI_PATTERNS_FILE = MEMORY_DIR / "anti_patterns.json"


def classify_failure(message: str) -> str:
    """根据中断原因关键词匹配反模式分类"""
    if not ANTI_PATTERNS_FILE.exists():
        return "unknown"
    try:
        with open(ANTI_PATTERNS_FILE, 'r', encoding='utf-8') as f:
            ap_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return "unknown"

    msg_lower = message.lower()
    for cat_id, cat_info in ap_data.get("categories", {}).items():
        if cat_id == "unknown":
            continue
        for kw in cat_info.get("keywords", []):
            if kw.lower() in msg_lower:
                return cat_id
    return "unknown"


def record_anti_pattern(feature_id: str, message: str, is_blocked: bool):
    """将失败记录沉淀到反模式库"""
    if not message:
        return
    if not ANTI_PATTERNS_FILE.exists():
        return
    try:
        with open(ANTI_PATTERNS_FILE, 'r', encoding='utf-8') as f:
            ap_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    category = "external_blocked" if is_blocked else classify_failure(message)
    entry = {
        "ts": datetime.now().isoformat(),
        "feature_id": feature_id,
        "category": category,
        "message": message,
    }
    ap_data.setdefault("history", []).append(entry)

    with open(ANTI_PATTERNS_FILE, 'w', encoding='utf-8') as f:
        json.dump(ap_data, f, ensure_ascii=False, indent=2)
