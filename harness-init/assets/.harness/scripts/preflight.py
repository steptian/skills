#!/usr/bin/env python3
"""
Preflight 环境快照 — 在每次 session 开始前采集工作区状态，
注入到 agent prompt 中，减少前几轮探索性动作。

输出: JSON 到 stdout（供 dev.sh 捕获）；同时落盘到 logs/preflight_*.json。

用法:
  python3 .harness/scripts/preflight.py [--save]
    --save  同时写入 .harness/logs/preflight_<timestamp>.json
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = HARNESS_DIR.parent


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or str(PROJECT_ROOT),
            timeout=timeout,
        )
        return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def _tool_version(name: str) -> str | None:
    path = shutil.which(name)
    if not path:
        return None
    ver = _run([name, "--version"])
    return ver.split("\n")[0] if ver else "installed"


def _git_info() -> dict:
    if not (PROJECT_ROOT / ".git").exists():
        return {"initialized": False}

    branch = _run(["git", "branch", "--show-current"])
    status_lines = _run(["git", "status", "--short"]).split("\n")
    status_lines = [l for l in status_lines if l.strip()]

    log_raw = _run(["git", "log", "--oneline", "-5"])
    recent_commits = [l for l in log_raw.split("\n") if l.strip()]

    uncommitted = len(status_lines)
    staged = sum(1 for l in status_lines if l and len(l) > 1 and l[0] != " " and l[0] != "?")
    untracked = sum(1 for l in status_lines if l.startswith("?"))

    return {
        "initialized": True,
        "branch": branch or "detached",
        "uncommitted_count": uncommitted,
        "staged_count": staged,
        "untracked_count": untracked,
        "status_preview": status_lines[:15],
        "recent_commits": recent_commits[:5],
    }


def _detect_project_type() -> dict:
    signals = {}
    marker_files = {
        "requirements.txt": "python-pip",
        "pyproject.toml": "python-modern",
        "setup.py": "python-legacy",
        "package.json": "nodejs",
        "go.mod": "golang",
        "Cargo.toml": "rust",
        "pom.xml": "java-maven",
        "build.gradle": "java-gradle",
        "Gemfile": "ruby",
        "composer.json": "php",
    }
    for filename, lang in marker_files.items():
        if (PROJECT_ROOT / filename).exists():
            signals[lang] = str(PROJECT_ROOT / filename)

    skill_dirs = [
        d.name for d in PROJECT_ROOT.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and (d / "SKILL.md").exists()
    ]
    if skill_dirs:
        signals["claude-skills"] = skill_dirs

    return signals


def _directory_summary(max_depth: int = 2) -> list[str]:
    entries = []
    for item in sorted(PROJECT_ROOT.iterdir()):
        name = item.name
        if name.startswith(".") and name not in (".harness",):
            continue
        if item.is_dir():
            child_count = sum(1 for _ in item.iterdir()) if item.is_dir() else 0
            entries.append(f"  {name}/ ({child_count} items)")
        else:
            size = item.stat().st_size
            entries.append(f"  {name} ({size}B)")
    return entries[:30]


def _harness_state() -> dict:
    features_file = HARNESS_DIR / "features.json"
    if not features_file.exists():
        return {"features_file": False}

    try:
        with open(features_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"features_file": "corrupted"}

    features = data.get("features", [])
    sessions = data.get("sessions", [])

    running_sessions = [s for s in sessions if s.get("status") == "running"]

    return {
        "features_file": True,
        "total_features": len(features),
        "completed": sum(1 for f in features if f.get("status") == "completed"),
        "in_progress": sum(1 for f in features if f.get("status") == "in_progress"),
        "pending": sum(1 for f in features if f.get("status") == "pending"),
        "blocked": sum(1 for f in features if f.get("status") == "blocked"),
        "total_sessions": len(sessions),
        "running_sessions": len(running_sessions),
    }


def collect() -> dict:
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "cwd": str(PROJECT_ROOT),
        "tools": {},
        "git": _git_info(),
        "project_type": _detect_project_type(),
        "directory_summary": _directory_summary(),
        "harness_state": _harness_state(),
    }

    for tool in ("python3", "node", "npm", "git", "rg", "claude"):
        ver = _tool_version(tool)
        if ver:
            snapshot["tools"][tool] = ver

    return snapshot


def format_for_prompt(snapshot: dict) -> str:
    lines = ["## 环境快照 (preflight)"]

    lines.append(f"- 工作目录: `{snapshot['cwd']}`")
    lines.append(f"- 采集时间: {snapshot['timestamp'][:19]}")

    if snapshot["tools"]:
        tools_str = ", ".join(
            f"{k}={v.split()[0] if ' ' in v else v}"
            for k, v in snapshot["tools"].items()
        )
        lines.append(f"- 可用工具: {tools_str}")

    git = snapshot.get("git", {})
    if git.get("initialized"):
        lines.append(f"- Git 分支: `{git.get('branch', '?')}`")
        lines.append(
            f"- 未提交: {git.get('uncommitted_count', 0)} "
            f"(staged: {git.get('staged_count', 0)}, "
            f"untracked: {git.get('untracked_count', 0)})"
        )
        commits = git.get("recent_commits", [])
        if commits:
            lines.append("- 最近提交:")
            for c in commits[:3]:
                lines.append(f"  - `{c}`")

    pt = snapshot.get("project_type", {})
    if pt:
        skills = pt.pop("claude-skills", None)
        if pt:
            lines.append(f"- 项目类型: {', '.join(pt.keys())}")
        if skills:
            lines.append(f"- Skills 目录: {', '.join(skills[:10])}")

    hs = snapshot.get("harness_state", {})
    if hs.get("features_file"):
        lines.append(
            f"- Harness: {hs.get('total_features', 0)} features "
            f"(done={hs.get('completed', 0)} wip={hs.get('in_progress', 0)} "
            f"pending={hs.get('pending', 0)}), "
            f"{hs.get('total_sessions', 0)} sessions "
            f"({hs.get('running_sessions', 0)} running)"
        )

    dirs = snapshot.get("directory_summary", [])
    if dirs:
        lines.append("- 根目录:")
        for d in dirs[:15]:
            lines.append(f"  {d}")

    return "\n".join(lines)


def main():
    save = "--save" in sys.argv

    snapshot = collect()

    if save:
        log_dir = HARNESS_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = log_dir / f"preflight_{ts}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"[preflight] saved → {out_path}", file=sys.stderr)

    if "--prompt" in sys.argv:
        print(format_for_prompt(snapshot))
    else:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
