#!/usr/bin/env python3
"""
黄金原则检查器 - 机械检查代码规范

用法:
  linter.py                    # 检查所有文件
  linter.py src/api/           # 检查指定目录
  linter.py --fix              # 自动修复
  linter.py --json             # JSON 输出
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

# ============================================================================
# 配置
# ============================================================================

DEFAULT_RULES = {
    "file_size": {"max_lines": 500, "severity": "warning"},
    "func_length": {"max_lines": 50, "severity": "warning"},
    "class_length": {"max_lines": 300, "severity": "warning"},
    "line_length": {"max_chars": 120, "severity": "warning"},
}

# 禁止模式
FORBIDDEN_PATTERNS = {
    "bare_except": {
        "pattern": r"except\s*:",
        "message": "禁止空 except 块，应明确捕获具体异常",
        "severity": "error",
        "fix": None,
    },
    "select_star": {
        "pattern": r"SELECT\s+\*\s+FROM",
        "message": "禁止 SELECT *，应明确指定字段",
        "severity": "warning",
        "fix": None,
    },
    "hardcoded_password": {
        "pattern": r"(password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]",
        "message": "禁止硬编码密码，应使用环境变量",
        "severity": "error",
        "fix": None,
    },
    "magic_number": {
        "pattern": r"(?<!self\.)(?<!\w)(\d{3,})(?!\w)",
        "message": "魔法数字应提取为常量",
        "severity": "info",
        "fix": None,
    },
    "todo_fixme": {
        "pattern": r"#\s*(TODO|FIXME|HACK|XXX):",
        "message": "发现待办标记",
        "severity": "info",
        "fix": None,
    },
}

# 可自动修复的模式
AUTO_FIXABLE = ["unused_import", "trailing_whitespace", "missing_newline"]


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    file: str
    line: int
    column: int
    rule: str
    severity: Severity
    message: str
    fix: Optional[str] = None

    def to_dict(self):
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "fix": self.fix,
        }


# ============================================================================
# 检查器
# ============================================================================


class Linter:
    def __init__(self, project_root: Path, config: Optional[dict] = None):
        self.project_root = project_root
        self.config = config or DEFAULT_RULES
        self.issues: List[Issue] = []

        # 尝试加载架构配置
        self.arch_config = self._load_architecture_config()

    def _load_architecture_config(self) -> Optional[dict]:
        """加载架构分层配置"""
        arch_file = self.project_root / ".harness" / "architecture.json"
        if arch_file.exists():
            try:
                with open(arch_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def lint(self, paths: List[Path], fix: bool = False) -> List[Issue]:
        """检查指定路径"""
        self.issues = []

        for path in paths:
            if path.is_file():
                self._lint_file(path, fix)
            elif path.is_dir():
                for ext in ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.java"]:
                    for file in path.rglob(ext):
                        if self._should_skip(file):
                            continue
                        self._lint_file(file, fix)

        return self.issues

    def _should_skip(self, path: Path) -> bool:
        """跳过不需要检查的文件"""
        skip_dirs = {
            "node_modules",
            "venv",
            ".venv",
            "__pycache__",
            ".git",
            "dist",
            "build",
            ".harness",
        }
        for part in path.parts:
            if part in skip_dirs:
                return True
        return False

    def _lint_file(self, filepath: Path, fix: bool = False):
        """检查单个文件"""
        try:
            content = filepath.read_text(encoding="utf-8")
            lines = content.split("\n")
        except (IOError, UnicodeDecodeError):
            return

        relative_path = str(filepath.relative_to(self.project_root))

        # 1. 文件大小检查
        max_lines = self.config["file_size"]["max_lines"]
        if len(lines) > max_lines:
            self.issues.append(
                Issue(
                    file=relative_path,
                    line=len(lines),
                    column=0,
                    rule="file_size",
                    severity=Severity.WARNING,
                    message=f"文件超过 {max_lines} 行 (实际: {len(lines)} 行)",
                    fix="考虑拆分为多个模块",
                )
            )

        # 2. 逐行检查
        for i, line in enumerate(lines, 1):
            # 行长度检查
            max_chars = self.config["line_length"]["max_chars"]
            if len(line) > max_chars:
                self.issues.append(
                    Issue(
                        file=relative_path,
                        line=i,
                        column=max_chars,
                        rule="line_length",
                        severity=Severity.INFO,
                        message=f"行超过 {max_chars} 字符 (实际: {len(line)})",
                    )
                )

            # 禁止模式检查
            for rule_name, rule_config in FORBIDDEN_PATTERNS.items():
                if re.search(rule_config["pattern"], line, re.IGNORECASE):
                    # 跳过某些误报
                    if rule_name == "magic_number" and re.match(
                        r"^\s*#", line
                    ):  # 注释中的数字
                        continue

                    self.issues.append(
                        Issue(
                            file=relative_path,
                            line=i,
                            column=0,
                            rule=rule_name,
                            severity=Severity(rule_config["severity"]),
                            message=rule_config["message"],
                            fix=rule_config.get("fix"),
                        )
                    )

        # 3. Python 特定检查
        if filepath.suffix == ".py":
            self._lint_python(filepath, lines, relative_path)

        # 4. 架构约束检查
        if self.arch_config:
            self._check_architecture(filepath, relative_path)

    def _lint_python(self, filepath: Path, lines: List[str], relative_path: str):
        """Python 特定检查"""
        # 检查函数长度
        func_pattern = re.compile(r"^\s*def\s+(\w+)\s*\(")
        in_func = False
        func_start = 0
        func_name = ""
        indent_level = 0

        for i, line in enumerate(lines, 1):
            match = func_pattern.match(line)
            if match:
                if in_func:
                    # 检查上一个函数长度
                    func_len = i - func_start
                    max_lines = self.config["func_length"]["max_lines"]
                    if func_len > max_lines:
                        self.issues.append(
                            Issue(
                                file=relative_path,
                                line=func_start,
                                column=0,
                                rule="func_length",
                                severity=Severity.WARNING,
                                message=f"函数 '{func_name}' 超过 {max_lines} 行 (实际: {func_len})",
                                fix="考虑拆分为多个小函数",
                            )
                        )
                in_func = True
                func_start = i
                func_name = match.group(1)
                indent_level = len(line) - len(line.lstrip())

        # 检查未使用的 import
        content = "\n".join(lines)
        import_pattern = re.compile(r"^import\s+(\w+)|^from\s+(\w+)", re.MULTILINE)
        for match in import_pattern.finditer(content):
            module = match.group(1) or match.group(2)
            # 简单检查：模块名是否在文件其他地方出现
            module_usage = re.search(rf"\b{module}\b", content[match.end() :])
            if not module_usage and module not in ["os", "sys", "re", "json", "pathlib"]:
                line_num = content[: match.start()].count("\n") + 1
                self.issues.append(
                    Issue(
                        file=relative_path,
                        line=line_num,
                        column=0,
                        rule="unused_import",
                        severity=Severity.INFO,
                        message=f"可能未使用的 import: {module}",
                        fix=f"移除 import {module}",
                    )
                )

    def _check_architecture(self, filepath: Path, relative_path: str):
        """检查架构约束"""
        if not self.arch_config:
            return

        layers = self.arch_config.get("layers", [])
        rules = self.arch_config.get("rules", {})

        # 判断文件属于哪一层
        file_layer = None
        for layer in layers:
            if f"/{layer}/" in relative_path or relative_path.startswith(f"{layer}/"):
                file_layer = layer
                break

        if not file_layer:
            return

        # 检查允许的依赖
        allowed_deps = rules.get(file_layer, [])
        if not allowed_deps:
            return

        try:
            content = filepath.read_text(encoding="utf-8")
        except IOError:
            return

        # 检查 import 语句
        import_pattern = re.compile(r"^(?:from|import)\s+([^\s.]+)", re.MULTILINE)
        for match in import_pattern.finditer(content):
            imported_module = match.group(1)

            # 检查是否导入了不允许的层
            for layer in layers:
                if layer in imported_module and layer not in allowed_deps:
                    self.issues.append(
                        Issue(
                            file=relative_path,
                            line=content[: match.start()].count("\n") + 1,
                            column=0,
                            rule="arch_violation",
                            severity=Severity.ERROR,
                            message=f"架构违规: {file_layer} 层不应导入 {layer} 层",
                            fix=f"将 {layer} 的调用移到允许的层",
                        )
                    )


# ============================================================================
# 输出格式化
# ============================================================================


def format_issues(issues: List[Issue], format_type: str = "text") -> str:
    """格式化输出"""
    if format_type == "json":
        return json.dumps([i.to_dict() for i in issues], indent=2, ensure_ascii=False)

    if not issues:
        return "✅ 没有发现问题"

    # 按严重程度分组
    errors = [i for i in issues if i.severity == Severity.ERROR]
    warnings = [i for i in issues if i.severity == Severity.WARNING]
    infos = [i for i in issues if i.severity == Severity.INFO]

    output = []

    if errors:
        output.append(f"❌ {len(errors)} 个错误:")
        for issue in errors:
            output.append(f"  {issue.file}:{issue.line} - {issue.message}")

    if warnings:
        output.append(f"⚠️  {len(warnings)} 个警告:")
        for issue in warnings:
            output.append(f"  {issue.file}:{issue.line} - {issue.message}")

    if infos:
        output.append(f"ℹ️  {len(infos)} 个建议:")
        for issue in infos:
            output.append(f"  {issue.file}:{issue.line} - {issue.message}")

    return "\n".join(output)


# ============================================================================
# 主入口
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="黄金原则检查器")
    parser.add_argument("paths", nargs="*", default=["."], help="要检查的路径")
    parser.add_argument("--fix", action="store_true", help="自动修复问题")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument(
        "--config", type=str, help="配置文件路径 (TODO: 未实现)"
    )

    args = parser.parse_args()

    # 确定项目根目录
    project_root = Path.cwd()
    while not (project_root / ".git").exists() and project_root.parent != project_root:
        project_root = project_root.parent

    # 解析路径
    paths = []
    for p in args.paths:
        path = Path(p)
        if not path.exists():
            print(f"警告: 路径不存在: {p}", file=sys.stderr)
            continue
        paths.append(path if path.is_absolute() else project_root / p)

    if not paths:
        print("错误: 没有有效的检查路径", file=sys.stderr)
        sys.exit(1)

    # 执行检查
    linter = Linter(project_root)
    issues = linter.lint(paths, fix=args.fix)

    # 输出结果
    format_type = "json" if args.json else "text"
    print(format_issues(issues, format_type))

    # 返回码
    errors = [i for i in issues if i.severity == Severity.ERROR]
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
