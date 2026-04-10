#!/usr/bin/env python3
"""
技术债花园 - 垃圾回收式技术债管理

用法:
  garden.py                    # 扫描并报告
  garden.py --auto             # 自动修复简单问题
  garden.py --create-todos     # 为复杂问题创建待办
  garden.py --json             # JSON 输出
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# ============================================================================
# 配置
# ============================================================================

# 可自动修复的问题类型
AUTO_FIXABLE = {
    "trailing_whitespace": "移除行尾空白",
    "missing_newline": "添加文件末尾换行",
    "double_blank_lines": "移除多余空行",
}

# 需要创建待办的问题类型
TODO_WORTHY = {
    "file_size": "文件过大，需要拆分",
    "func_length": "函数过长，需要重构",
    "arch_violation": "架构违规，需要调整",
}


@dataclass
class DebtItem:
    """技术债条目"""
    type: str
    file: str
    line: int
    message: str
    severity: str  # high, medium, low
    auto_fixable: bool
    fix_description: Optional[str] = None

    def to_dict(self):
        return {
            "type": self.type,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "severity": self.severity,
            "auto_fixable": self.auto_fixable,
            "fix_description": self.fix_description,
        }


# ============================================================================
# 扫描器
# ============================================================================


class GardenScanner:
    """技术债扫描器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.debts: List[DebtItem] = []
        self.harness_dir = project_root / ".harness"
        self.features_file = self.harness_dir / "features.json"

    def scan(self) -> List[DebtItem]:
        """扫描代码库"""
        self.debts = []

        # 1. 运行 linter 获取基础问题
        self._run_linter()

        # 2. 扫描文档一致性
        self._check_docs_sync()

        # 3. 扫描 TODO/FIXME
        self._scan_todos()

        return self.debts

    def _run_linter(self):
        """运行 linter 并收集问题"""
        linter_path = self.harness_dir / "scripts" / "linter.py"
        if not linter_path.exists():
            return

        try:
            result = subprocess.run(
                ["python3", str(linter_path), "--json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                issues = json.loads(result.stdout)
                for issue in issues:
                    self.debts.append(
                        DebtItem(
                            type=issue["rule"],
                            file=issue["file"],
                            line=issue["line"],
                            message=issue["message"],
                            severity=self._severity_from_linter(issue["severity"]),
                            auto_fixable=issue["rule"] in AUTO_FIXABLE,
                            fix_description=issue.get("fix"),
                        )
                    )
        except (json.JSONDecodeError, subprocess.SubprocessError):
            pass

    def _severity_from_linter(self, severity: str) -> str:
        """转换严重程度"""
        mapping = {"error": "high", "warning": "medium", "info": "low"}
        return mapping.get(severity, "low")

    def _check_docs_sync(self):
        """检查文档与代码同步"""
        readme = self.project_root / "README.md"
        if not readme.exists():
            return

        content = readme.read_text(encoding="utf-8")
        # 查找代码块中引用的文件
        file_refs = re.findall(r"(?:cat|vim|code)\s+([^\s;&|`]+)", content)
        for ref in file_refs:
            ref = ref.strip()
            if not ref or ref.startswith("$"):
                continue
            if not (self.project_root / ref).exists():
                self.debts.append(
                    DebtItem(
                        type="doc_outdated",
                        file="README.md",
                        line=0,
                        message=f"文档引用的文件不存在: {ref}",
                        severity="medium",
                        auto_fixable=False,
                    )
                )

    def _scan_todos(self):
        """扫描 TODO/FIXME 标记"""
        for ext in ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx"]:
            for filepath in self.project_root.rglob(ext):
                if self._should_skip(filepath):
                    continue

                try:
                    content = filepath.read_text(encoding="utf-8")
                    lines = content.split("\n")
                except (IOError, UnicodeDecodeError):
                    continue

                for i, line in enumerate(lines, 1):
                    match = re.search(r"#\s*(TODO|FIXME|HACK|XXX):\s*(.+)", line, re.IGNORECASE)
                    if match:
                        tag, desc = match.groups()
                        self.debts.append(
                            DebtItem(
                                type=f"todo_{tag.lower()}",
                                file=str(filepath.relative_to(self.project_root)),
                                line=i,
                                message=f"{tag}: {desc}",
                                severity="low" if tag.lower() == "todo" else "medium",
                                auto_fixable=False,
                            )
                        )

    def _should_skip(self, path: Path) -> bool:
        """跳过不需要检查的文件"""
        skip_dirs = {
            "node_modules", "venv", ".venv", "__pycache__",
            ".git", "dist", "build", ".harness",
        }
        return any(part in skip_dirs for part in path.parts)


# ============================================================================
# 自动修复
# ============================================================================


class AutoFixer:
    """自动修复器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.fixed_count = 0

    def fix(self, debts: List[DebtItem]) -> List[DebtItem]:
        """自动修复可修复的问题"""
        remaining = []

        for debt in debts:
            if not debt.auto_fixable:
                remaining.append(debt)
                continue

            if self._fix_debt(debt):
                self.fixed_count += 1
            else:
                remaining.append(debt)

        return remaining

    def _fix_debt(self, debt: DebtItem) -> bool:
        """修复单个问题"""
        filepath = self.project_root / debt.file
        if not filepath.exists():
            return False

        try:
            content = filepath.read_text(encoding="utf-8")
            lines = content.split("\n")
        except (IOError, UnicodeDecodeError):
            return False

        modified = False

        if debt.type == "trailing_whitespace":
            new_lines = [line.rstrip() for line in lines]
            if new_lines != lines:
                lines = new_lines
                modified = True

        elif debt.type == "missing_newline":
            if lines and lines[-1] != "":
                lines.append("")
                modified = True

        elif debt.type == "double_blank_lines":
            new_lines = []
            prev_blank = False
            for line in lines:
                is_blank = line.strip() == ""
                if is_blank and prev_blank:
                    continue
                new_lines.append(line)
                prev_blank = is_blank
            if new_lines != lines:
                lines = new_lines
                modified = True

        if modified:
            filepath.write_text("\n".join(lines), encoding="utf-8")
            print(f"  ✅ 修复: {debt.file} ({debt.type})")

        return modified


# ============================================================================
# 待办创建
# ============================================================================


class TodoCreator:
    """为技术债创建待办事项"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.features_file = project_root / ".harness" / "features.json"

    def create_todos(self, debts: List[DebtItem]) -> List[str]:
        """为值得追踪的技术债创建待办"""
        created_ids = []

        if not self.features_file.exists():
            return created_ids

        try:
            with open(self.features_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return created_ids

        # 获取现有 ID
        existing_ids = [f["id"] for f in data.get("features", [])]
        max_num = 0
        for fid in existing_ids:
            if fid.startswith("F") and fid[1:].isdigit():
                max_num = max(max_num, int(fid[1:]))

        # 为值得追踪的问题创建待办
        for debt in debts:
            if debt.type not in TODO_WORTHY:
                continue

            max_num += 1
            new_id = f"F{max_num:03d}"

            new_feature = {
                "id": new_id,
                "priority": "medium" if debt.severity == "high" else "low",
                "status": "pending",
                "description": f"[技术债] {debt.message}",
                "steps": [
                    f"定位: {debt.file}:{debt.line}",
                    "分析根因",
                    "实施修复",
                    "验证",
                ],
                "acceptance_criteria": [f"修复 {debt.type} 问题"],
                "dependencies": [],
                "type": "tech_debt",
                "source": "garden",
                "created_at": datetime.now().isoformat(),
            }

            data.setdefault("features", []).append(new_feature)
            created_ids.append(new_id)
            print(f"  📝 创建: [{new_id}] {debt.message}")

        if created_ids:
            with open(self.features_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return created_ids


# ============================================================================
# 输出格式化
# ============================================================================


def format_report(debts: List[DebtItem], fixed_count: int = 0, format_type: str = "text") -> str:
    """格式化报告"""
    if format_type == "json":
        return json.dumps(
            {"total": len(debts), "fixed": fixed_count, "debts": [d.to_dict() for d in debts]},
            indent=2, ensure_ascii=False,
        )

    lines = ["🌿 Harness Garden - 技术债扫描", "━" * 50]

    if not debts and fixed_count == 0:
        lines.append("✅ 代码库干净，没有发现技术债")
        return "\n".join(lines)

    # 按严重程度分组
    high = [d for d in debts if d.severity == "high"]
    medium = [d for d in debts if d.severity == "medium"]
    low = [d for d in debts if d.severity == "low"]

    lines.append("")
    lines.append("扫描结果:")
    if high:
        lines.append(f"  🔴 {len(high)} 个高优先级")
    if medium:
        lines.append(f"  🟡 {len(medium)} 个中优先级")
    if low:
        lines.append(f"  🟢 {len(low)} 个低优先级")

    if fixed_count > 0:
        lines.append(f"\n✅ 已自动修复: {fixed_count} 个问题")

    if debts:
        lines.append("\n需要处理:")
        for debt in debts[:10]:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(debt.severity, "⚪")
            lines.append(f"  {icon} {debt.file}:{debt.line} - {debt.message}")
        if len(debts) > 10:
            lines.append(f"  ... 还有 {len(debts) - 10} 个")

    return "\n".join(lines)


# ============================================================================
# 主入口
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="技术债花园")
    parser.add_argument("--auto", action="store_true", help="自动修复")
    parser.add_argument("--create-todos", action="store_true", help="创建待办")
    parser.add_argument("--json", action="store_true", help="JSON 输出")

    args = parser.parse_args()

    # 确定项目根目录
    project_root = Path.cwd()
    while not (project_root / ".git").exists() and project_root.parent != project_root:
        project_root = project_root.parent

    # 扫描
    scanner = GardenScanner(project_root)
    debts = scanner.scan()
    fixed_count = 0

    # 自动修复
    if args.auto:
        print("🔧 自动修复中...")
        fixer = AutoFixer(project_root)
        debts = fixer.fix(debts)
        fixed_count = fixer.fixed_count

    # 创建待办
    if args.create_todos and debts:
        print("\n📝 创建待办...")
        creator = TodoCreator(project_root)
        creator.create_todos(debts)

    # 输出报告
    print(format_report(debts, fixed_count, "json" if args.json else "text"))


if __name__ == "__main__":
    main()
