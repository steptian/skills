#!/usr/bin/env python3
"""
Harness Bench 评测对比脚本

用法:
  eval.py run     --tag <tag> [--tasks <dir>]   运行一轮评测
  eval.py compare <tag_a> <tag_b>               对比两轮结果
  eval.py list                                  列出历史评测
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
TASKS_DIR = BENCH_DIR / "tasks"
RESULTS_DIR = BENCH_DIR / "results"


def load_tasks(tasks_dir: Path) -> list[dict]:
    tasks = []
    for f in sorted(tasks_dir.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                tasks.append(json.load(fh))
        except (json.JSONDecodeError, IOError) as e:
            print(f"[warn] 跳过 {f.name}: {e}", file=sys.stderr)
    return tasks


def cmd_run(args):
    tag = args.tag
    tasks_dir = Path(args.tasks) if args.tasks else TASKS_DIR

    tasks = load_tasks(tasks_dir)
    if not tasks:
        print("没有找到任务定义文件")
        return

    print(f"评测标签: {tag}")
    print(f"任务数量: {len(tasks)}")
    print()

    results = {
        "tag": tag,
        "timestamp": datetime.now().isoformat(),
        "task_count": len(tasks),
        "tasks": [],
        "summary": {},
    }

    for task in tasks:
        tid = task["id"]
        print(f"  [{tid}] {task.get('name', '?')} ... ", end="", flush=True)

        result = {
            "task_id": tid,
            "name": task.get("name"),
            "category": task.get("category"),
            "difficulty": task.get("difficulty"),
            "status": "pending",
            "turns": 0,
            "duration_sec": 0,
            "notes": "",
        }

        print("⏳ (手动记录)")
        result["status"] = "manual"
        results["tasks"].append(result)

    success = sum(1 for r in results["tasks"] if r["status"] == "success")
    total = len(results["tasks"])
    results["summary"] = {
        "success_rate": success / max(total, 1),
        "total": total,
        "success": success,
        "avg_turns": 0,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"{tag}_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {out_path}")
    print(f"成功率: {success}/{total} ({success / max(total, 1) * 100:.1f}%)")


def cmd_compare(args):
    tag_a = args.tag_a
    tag_b = args.tag_b

    def find_latest(tag: str) -> dict | None:
        matches = sorted(RESULTS_DIR.glob(f"{tag}_*.json"), reverse=True)
        if not matches:
            return None
        with open(matches[0], "r", encoding="utf-8") as f:
            return json.load(f)

    a = find_latest(tag_a)
    b = find_latest(tag_b)

    if not a:
        print(f"找不到标签 '{tag_a}' 的结果")
        return
    if not b:
        print(f"找不到标签 '{tag_b}' 的结果")
        return

    sa = a.get("summary", {})
    sb = b.get("summary", {})

    print(f"{'指标':<25} {'[' + tag_a + ']':>12} {'[' + tag_b + ']':>12} {'变化':>12}")
    print("-" * 65)

    for key in ("success_rate", "avg_turns", "success", "total"):
        va = sa.get(key, 0)
        vb = sb.get(key, 0)
        if isinstance(va, float):
            delta = vb - va
            sign = "+" if delta > 0 else ""
            print(f"  {key:<23} {va:>11.1%} {vb:>11.1%} {sign}{delta:>10.1%}")
        else:
            delta = vb - va
            sign = "+" if delta > 0 else ""
            print(f"  {key:<23} {va:>12} {vb:>12} {sign}{delta:>11}")

    a_tasks = {r["task_id"]: r for r in a.get("tasks", [])}
    b_tasks = {r["task_id"]: r for r in b.get("tasks", [])}
    regressions = []
    improvements = []
    for tid in a_tasks:
        if tid in b_tasks:
            ra, rb = a_tasks[tid], b_tasks[tid]
            if ra["status"] == "success" and rb["status"] != "success":
                regressions.append(tid)
            elif ra["status"] != "success" and rb["status"] == "success":
                improvements.append(tid)

    if regressions:
        print(f"\n⚠ 退化 ({len(regressions)}): {', '.join(regressions)}")
    if improvements:
        print(f"\n✅ 改进 ({len(improvements)}): {', '.join(improvements)}")
    if not regressions and not improvements:
        print("\n无退化/改进变化")


def cmd_list(_args):
    if not RESULTS_DIR.exists():
        print("暂无评测结果")
        return

    files = sorted(RESULTS_DIR.glob("*.json"), reverse=True)
    if not files:
        print("暂无评测结果")
        return

    print(f"{'标签':<15} {'时间':<20} {'成功率':>10} {'文件'}")
    print("-" * 65)
    for f in files[:20]:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            tag = data.get("tag", "?")
            ts = data.get("timestamp", "?")[:19]
            sr = data.get("summary", {}).get("success_rate", 0)
            print(f"  {tag:<13} {ts:<20} {sr:>9.1%} {f.name}")
        except (json.JSONDecodeError, IOError):
            print(f"  {'?':<13} {'?':<20} {'?':>10} {f.name}")


def main():
    parser = argparse.ArgumentParser(description="Harness Bench 评测工具")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("run", help="运行评测")
    p.add_argument("--tag", required=True, help="评测标签 (如 v1, v2)")
    p.add_argument("--tasks", help="任务目录路径")

    p = sub.add_parser("compare", help="对比两轮评测")
    p.add_argument("tag_a", help="A 版本标签")
    p.add_argument("tag_b", help="B 版本标签")

    sub.add_parser("list", help="列出历史评测")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
