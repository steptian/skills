"""
经验教训管理模块 - 反思沉淀 + 规则进化

提供：
  1. cmd_learn  - 安全写入教训到 learnings.json（文件锁 + 原子写入）
  2. cmd_evolve - 扫描教训和反模式，输出规则变更建议
"""

import json
import os
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path  # noqa: F401 — preserved for future use

from .core import C, HARNESS_DIR, MEMORY_DIR, LOCK_FILE

LEARNINGS_FILE = MEMORY_DIR / "learnings.json"
MAX_LEARNINGS = 100
MIN_CONFIDENCE_INJECT = 6
MAX_INJECT_COUNT = 5


def _atomic_write_json(filepath, data):
    """原子写入 JSON 文件：写临时文件再 rename，避免半写状态。"""
    MEMORY_DIR.mkdir(exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', dir=filepath.parent, suffix='.tmp',
            delete=False, encoding='utf-8'
        ) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write('\n')
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        os.replace(tmp_path, str(filepath))
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _load_learnings():
    """读取 learnings.json，文件不存在或损坏时返回空结构。"""
    if not LEARNINGS_FILE.exists():
        return {"entries": []}
    try:
        with open(LEARNINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data.setdefault('entries', [])
        return data
    except (json.JSONDecodeError, IOError):
        return {"entries": []}


def cmd_learn(args):
    """记录经验教训到 learnings.json"""
    import fcntl

    # 对 LOCK_FILE 加全局锁
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, 'w') as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            data = _load_learnings()
            entries = data.get('entries', [])

            # 计算下一个 ID
            max_num = 0
            for e in entries:
                eid = e.get('id', '')
                if eid.startswith('L') and eid[1:].isdigit():
                    max_num = max(max_num, int(eid[1:]))

            confidence = min(10, max(1, args.confidence))

            new_entry = {
                "id": f"L{max_num + 1:03d}",
                "ts": datetime.now().isoformat(),
                "feature_id": getattr(args, 'feature_id', '') or '',
                "category": args.category,
                "lesson": args.lesson,
                "context": args.context or '',
                "confidence": confidence,
                "injected": 0,
            }
            entries.append(new_entry)

            # 增长控制：超过上限时淘汰低价值条目
            if len(entries) > MAX_LEARNINGS:
                entries.sort(key=lambda e: (e.get('injected', 0), e.get('confidence', 0)))
                entries = entries[-MAX_LEARNINGS:]

            data['entries'] = entries
            _atomic_write_json(LEARNINGS_FILE, data)
            print(f"{C.G}✓ 教训已记录: {args.lesson}{C.N}")
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def cmd_evolve(_args):
    """分析经验教训，建议框架规则进化"""
    learnings = _load_learnings().get('entries', [])

    # 读取 anti_patterns
    anti_patterns_file = MEMORY_DIR / "anti_patterns.json"
    anti_patterns = {"categories": {}, "history": []}
    if anti_patterns_file.exists():
        try:
            with open(anti_patterns_file, 'r', encoding='utf-8') as f:
                anti_patterns = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # 读取 GOLDEN_RULES（用于显示参考）
    golden_rules_file = HARNESS_DIR / "GOLDEN_RULES.md"
    rules_count = 0
    if golden_rules_file.exists():
        try:
            rules_count = len([
                l for l in golden_rules_file.read_text().split('\n')
                if l.strip().startswith('|') and '---' not in l
            ])
        except IOError:
            pass

    # 分析模式
    cat_counts = Counter(e.get('category') for e in learnings if e.get('category'))
    ap_cat_counts = Counter(
        e.get('category') for e in anti_patterns.get('history', [])
        if e.get('category')
    )

    suggestions = []

    # 同类教训出现 3+ 次 → 建议新增规则
    for cat, count in cat_counts.items():
        if count >= 3:
            examples = [e['lesson'] for e in learnings if e.get('category') == cat][:3]
            suggestions.append(('NEW', cat, count, examples))

    # anti_patterns 某类高频 → 建议强化
    for cat, count in ap_cat_counts.items():
        if count >= 3:
            cat_info = anti_patterns.get('categories', {}).get(cat, {})
            suggestions.append((
                'REINFORCE',
                cat_info.get('label', cat),
                count,
                [cat_info.get('countermeasure', '')],
            ))

    # 输出报告
    print(f"Framework Evolution Report")
    print(f"{'='*40}")
    print(f"\n  教训总数: {len(learnings)} | "
          f"反模式记录: {len(anti_patterns.get('history', []))} | "
          f"规则条目: {rules_count}")

    if suggestions:
        action_labels = {
            'NEW': '[NEW] 建议新增规则',
            'REINFORCE': '[REINFORCE] 建议强化规则',
        }
        for action, label, count, examples in suggestions:
            print(f"\n  {action_labels.get(action, action)}:")
            print(f"    → {label} (来源: {count} 条记录)")
            for ex in examples:
                if ex:
                    print(f"      - {ex[:80]}")
    else:
        print(f"\n  暂无建议（数据积累不足，需要同类教训出现 3 次以上）")

    # 版本信息
    version_file = HARNESS_DIR / "VERSION"
    current_version = "unknown"
    if version_file.exists():
        try:
            current_version = version_file.read_text().strip()
        except IOError:
            pass
    print(f"\n  框架版本: {current_version}")
    print(f"  提示: 手动检查模型能力变化，决定是否简化 prompt")


def inject_learnings_to_stdout():
    """在 cmd_begin 中调用，将最近教训输出到 stdout（只读）。"""
    if not LEARNINGS_FILE.exists():
        return

    try:
        with open(LEARNINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        entries = data.get('entries', [])

        # 按时间倒序，过滤 confidence >= 6，取最近 5 条
        qualified = [e for e in entries if e.get('confidence', 0) >= MIN_CONFIDENCE_INJECT]
        recent = sorted(qualified, key=lambda e: e.get('ts', ''), reverse=True)[:MAX_INJECT_COUNT]

        if recent:
            print(f"\n--- PRIOR LEARNINGS ---")
            for entry in recent:
                print(f"  [{entry.get('category', '?')}] {entry.get('lesson', '')}")
                ctx = entry.get('context', '')
                if ctx:
                    print(f"    Context: {ctx[:80]}")
            print(f"--- END LEARNINGS ---")
    except (json.JSONDecodeError, IOError):
        pass
