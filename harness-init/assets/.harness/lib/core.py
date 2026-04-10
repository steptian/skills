"""
feature_cli 核心模块 - 安全 IO 层与配置

提供：
  1. 原子写入（写临时文件再 rename）
  2. 文件锁（防止多进程同时写入）
  3. 自动备份（每次写入前保留快照）
  4. 统计自动重算
"""

import json
import os
import shutil
import sys
import tempfile
import fcntl
from datetime import datetime
from pathlib import Path

HARNESS_DIR = Path(__file__).parent.parent
FEATURES_FILE = HARNESS_DIR / "features.json"
LEGACY_FILE = HARNESS_DIR / "feature_list.json"
LOCK_FILE = HARNESS_DIR / ".features.lock"
BACKUP_DIR = HARNESS_DIR / ".backups"
CONFIG_FILE = HARNESS_DIR / "config.json"
MEMORY_DIR = HARNESS_DIR / "memory"
MAX_BACKUPS = 20

def _read_version():
    """从 VERSION 文件读取版本号，文件不存在时返回 fallback"""
    version_file = HARNESS_DIR / "VERSION"
    try:
        return version_file.read_text().strip()
    except (IOError, OSError):
        return "0.0.0-unknown"


VERSION = _read_version()

# 默认配置
DEFAULT_CONFIG = {
    "max_sessions": 10,
    "stale_hours": 24,
    "auto_commit": True,
    "claude_args": "--dangerously-skip-permissions",
    "interactive": True,
    "auto_confirm": False,
}


class C:
    R = '\033[0;31m'
    G = '\033[0;32m'
    Y = '\033[1;33m'
    B = '\033[0;34m'
    W = '\033[0;36m'
    CYAN = '\033[0;36m'
    N = '\033[0m'


def load_config():
    """加载配置文件，合并默认值"""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                config.update(user_config)
        except (json.JSONDecodeError, IOError):
            pass
    return config


CONFIG = load_config()


def _resolve_file():
    """兼容旧文件名：优先用 features.json，回退 feature_list.json"""
    if FEATURES_FILE.exists():
        return FEATURES_FILE
    if LEGACY_FILE.exists():
        return LEGACY_FILE
    return FEATURES_FILE


def safe_load():
    path = _resolve_file()
    if not path.exists():
        print(f"{C.R}错误: {path} 不存在{C.N}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"{C.R}错误: JSON 格式损坏 - {e}{C.N}", file=sys.stderr)
        print(f"运行 `feature_cli.py recover` 从备份恢复", file=sys.stderr)
        sys.exit(1)
    data.setdefault('features', [])
    data.setdefault('sessions', [])
    data.setdefault('project', {})
    return data


def _recompute_stats(data):
    features = data.get('features', [])
    data['statistics'] = {
        'total': len(features),
        'completed': sum(1 for f in features if f.get('status') == 'completed'),
        'in_progress': sum(1 for f in features if f.get('status') == 'in_progress'),
        'pending': sum(1 for f in features if f.get('status') == 'pending'),
        'blocked': sum(1 for f in features if f.get('status') == 'blocked'),
    }
    return data


def _backup():
    path = _resolve_file()
    if not path.exists():
        return
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(path, BACKUP_DIR / f'features_{ts}.json')
    backups = sorted(BACKUP_DIR.glob('features_*.json'))
    for old in backups[:-MAX_BACKUPS]:
        old.unlink()


def _safe_write(data):
    _backup()
    data = _recompute_stats(data)
    target = FEATURES_FILE
    with tempfile.NamedTemporaryFile(
        mode='w', dir=target.parent, suffix='.tmp',
        delete=False, encoding='utf-8'
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write('\n')
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    os.replace(tmp_path, str(target))
    if LEGACY_FILE.exists() and LEGACY_FILE != target:
        LEGACY_FILE.unlink()


def locked_update(updater_fn):
    """读-改-写 + 文件锁，返回更新后的 data"""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, 'w') as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            data = safe_load()
            data = updater_fn(data)
            _safe_write(data)
            return data
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def format_log_entry(message, log_type="progress"):
    """创建结构化日志条目"""
    return {
        "ts": datetime.now().isoformat(),
        "type": log_type,
        "message": message,
    }


def log_display(entry):
    """统一显示日志条目（兼容纯字符串和结构化对象）"""
    if isinstance(entry, dict):
        ts = entry.get("ts", "")[:16].replace("T", " ")
        return f"[{ts}] {entry.get('message', '')}"
    return str(entry)


def compare_versions(v1: str, v2: str) -> int:
    """比较两个语义化版本号。返回: 1(v1>v2), 0(相等), -1(v1<v2)"""
    def parse(v):
        parts = []
        for p in v.split('.'):
            # 处理类似 "2.1.0-rc1" 的预发布标签
            num = ''.join(c for c in p if c.isdigit())
            parts.append(int(num) if num else 0)
        return parts
    a, b = parse(v1), parse(v2)
    for i in range(max(len(a), len(b))):
        x, y = a[i] if i < len(a) else 0, b[i] if i < len(b) else 0
        if x > y:
            return 1
        elif x < y:
            return -1
    return 0


def check_for_update() -> dict:
    """检查是否有可用更新。返回 {'current': str, 'latest': str, 'has_update': bool}"""
    source_version_file = Path.home() / ".claude" / "skills" / "harness-init" / "assets" / ".harness" / "VERSION"
    latest = ""
    if source_version_file.exists():
        try:
            latest = source_version_file.read_text().strip()
        except (IOError, OSError):
            pass
    return {
        "current": VERSION,
        "latest": latest or VERSION,
        "has_update": compare_versions(latest or VERSION, VERSION) > 0,
    }
