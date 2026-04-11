"""
原子 IO 共享模块 - 提供所有文件操作的安全基础

所有对 .harness 数据文件的写入都应通过此模块。

保证：
  1. 原子写入（tmpfile + fsync + rename，不会出现半写状态）
  2. 异常安全（写入失败时清理临时文件）
  3. 目录自动创建（父目录不存在时自动 mkdir）
"""

import json
import os
import tempfile
from pathlib import Path


def safe_write_json(filepath, data, indent=2):
    """原子写入 JSON 文件。

    流程：写入临时文件 → fsync → rename 原子替换。
    即使在写入过程中断电或进程崩溃，目标文件也不会损坏。
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', dir=filepath.parent, suffix='.tmp',
            delete=False, encoding='utf-8'
        ) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=indent)
            tmp.write('\n')
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        os.replace(tmp_path, str(filepath))
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def append_jsonl(filepath, entry):
    """原子追加一条记录到 JSONL 文件（每行一个 JSON 对象）。

    用于会话日志等追加频繁的场景。
    每次 append 后 fsync，确保数据不丢失。
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def read_json(filepath):
    """安全读取 JSON 文件，文件不存在或损坏时返回 None。"""
    filepath = Path(filepath)
    if not filepath.exists():
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
