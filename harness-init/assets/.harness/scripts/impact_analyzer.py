#!/usr/bin/env python3
"""
代码修改影响范围分析器 - 分析代码变更的影响范围，提供测试覆盖建议。

核心功能：
  1. 检测 Git 变更（staged/unstaged/committed）
  2. 分析文件依赖关系（import/call graph）
  3. 识别受影响的测试文件
  4. 生成测试覆盖建议

用法:
  python3 .harness/scripts/impact_analyzer.py                    # 分析当前变更
  python3 .harness/scripts/impact_analyzer.py --staged         # 分析已暂存变更
  python3 .harness/scripts/impact_analyzer.py --commit HEAD~1  # 分析最近提交
  python3 .harness/scripts/impact_analyzer.py --json           # JSON 输出
  python3 .harness/scripts/impact_analyzer.py --suggest-tests  # 仅输出测试建议
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ============================================================================
# 数据结构
# ============================================================================

class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class FileChange:
    path: str
    change_type: ChangeType
    old_path: Optional[str] = None  # for rename
    diff_summary: str = ""


@dataclass
class DependencyRelation:
    source: str  # 源文件
    target: str  # 目标文件（被依赖）
    relation_type: str  # "import", "call", "inherit"
    line_number: int = 0


@dataclass
class ImpactAnalysis:
    changed_files: List[FileChange] = field(default_factory=list)
    direct_dependents: Dict[str, List[str]] = field(default_factory=dict)  # 文件 -> 直接依赖它的文件
    transitive_dependents: Dict[str, List[str]] = field(default_factory=dict)  # 文件 -> 所有依赖它的文件（传递）
    affected_tests: List[str] = field(default_factory=list)
    test_coverage_gaps: List[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TestSuggestion:
    test_file: str
    priority: str  # "critical", "high", "medium", "low"
    reason: str
    related_changes: List[str] = field(default_factory=list)


# ============================================================================
# Git 变更检测
# ============================================================================

class GitChangeDetector:
    """检测 Git 变更"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def _run_git(self, cmd: List[str]) -> str:
        """运行 Git 命令"""
        try:
            result = subprocess.run(
                ["git"] + cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            return ""

    def is_git_repo(self) -> bool:
        """检查是否是 Git 仓库"""
        return (self.project_root / ".git").exists()

    def get_staged_changes(self) -> List[FileChange]:
        """获取已暂存的变更"""
        output = self._run_git(["diff", "--cached", "--name-status"])
        return self._parse_git_status(output)

    def get_unstaged_changes(self) -> List[FileChange]:
        """获取未暂存的变更"""
        output = self._run_git(["diff", "--name-status"])
        return self._parse_git_status(output)

    def get_all_changes(self) -> List[FileChange]:
        """获取所有变更（staged + unstaged）"""
        staged = self.get_staged_changes()
        unstaged = self.get_unstaged_changes()

        # 合并，避免重复
        staged_paths = {c.path for c in staged}
        combined = staged.copy()
        for c in unstaged:
            if c.path not in staged_paths:
                combined.append(c)
        return combined

    def get_commit_changes(self, commit: str) -> List[FileChange]:
        """获取指定提交的变更"""
        output = self._run_git(["show", "--name-status", commit])
        return self._parse_git_status(output)

    def _parse_git_status(self, output: str) -> List[FileChange]:
        """解析 git status 输出"""
        changes = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue

            status = parts[0]
            path = parts[1]
            old_path = parts[2] if len(parts) > 2 else None

            if status.startswith("A"):
                change_type = ChangeType.ADDED
            elif status.startswith("M"):
                change_type = ChangeType.MODIFIED
            elif status.startswith("D"):
                change_type = ChangeType.DELETED
            elif status.startswith("R"):
                change_type = ChangeType.RENAMED
            else:
                change_type = ChangeType.MODIFIED

            changes.append(FileChange(
                path=path,
                change_type=change_type,
                old_path=old_path,
            ))
        return changes

    def get_file_diff(self, filepath: str, staged: bool = False) -> str:
        """获取文件的 diff 内容"""
        args = ["diff"]
        if staged:
            args.append("--cached")
        args.extend(["--", filepath])
        return self._run_git(args)


# ============================================================================
# 依赖关系分析
# ============================================================================

class DependencyAnalyzer:
    """分析代码依赖关系"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.dependencies: List[DependencyRelation] = []
        self.file_modules: Dict[str, str] = {}  # 文件路径 -> 模块名

    def analyze_project(self, files: Optional[List[str]] = None) -> List[DependencyRelation]:
        """分析项目依赖关系"""
        self.dependencies = []

        if files:
            # 只分析指定文件
            target_files = [self.project_root / f for f in files if (self.project_root / f).exists()]
        else:
            # 分析所有 Python/TS/JS 文件
            target_files = []
            for ext in ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx"]:
                target_files.extend(self.project_root.rglob(ext))

        for filepath in target_files:
            if self._should_skip(filepath):
                continue
            self._analyze_file(filepath)

        return self.dependencies

    def _should_skip(self, filepath: Path) -> bool:
        """判断是否跳过该文件"""
        skip_dirs = {"node_modules", "venv", ".venv", "__pycache__", ".git", "dist", "build", ".harness"}
        for part in filepath.parts:
            if part in skip_dirs:
                return True
        return False

    def _analyze_file(self, filepath: Path):
        """分析单个文件的依赖关系"""
        try:
            content = filepath.read_text(encoding="utf-8")
        except (IOError, UnicodeDecodeError):
            return

        relative_path = str(filepath.relative_to(self.project_root))

        if filepath.suffix == ".py":
            self._analyze_python_imports(relative_path, content)
        elif filepath.suffix in [".ts", ".tsx", ".js", ".jsx"]:
            self._analyze_js_imports(relative_path, content)

    def _analyze_python_imports(self, filepath: str, content: str):
        """分析 Python import 语句"""
        # import module
        import_pattern = re.compile(r"^import\s+([\w\.]+)", re.MULTILINE)
        # from module import something
        from_pattern = re.compile(r"^from\s+([\w\.]+)\s+import", re.MULTILINE)

        for line_num, line in enumerate(content.split("\n"), 1):
            # import module
            match = import_pattern.match(line)
            if match:
                module = match.group(1)
                target_file = self._resolve_python_module(module, filepath)
                if target_file:
                    self.dependencies.append(DependencyRelation(
                        source=filepath,
                        target=target_file,
                        relation_type="import",
                        line_number=line_num,
                    ))

            # from module import
            match = from_pattern.match(line)
            if match:
                module = match.group(1)
                target_file = self._resolve_python_module(module, filepath)
                if target_file:
                    self.dependencies.append(DependencyRelation(
                        source=filepath,
                        target=target_file,
                        relation_type="import",
                        line_number=line_num,
                    ))

    def _analyze_js_imports(self, filepath: str, content: str):
        """分析 JavaScript/TypeScript import 语句"""
        # import ... from 'module'
        import_pattern = re.compile(r"^import\s.+from\s+['\"]([^\'\"]+)['\"]", re.MULTILINE)
        # require('module')
        require_pattern = re.compile(r"require\s*\(\s*['\"]([^\'\"]+)['\"]\s*\)", re.MULTILINE)

        for line_num, line in enumerate(content.split("\n"), 1):
            match = import_pattern.search(line)
            if match:
                module = match.group(1)
                target_file = self._resolve_js_module(module, filepath)
                if target_file:
                    self.dependencies.append(DependencyRelation(
                        source=filepath,
                        target=target_file,
                        relation_type="import",
                        line_number=line_num,
                    ))

            match = require_pattern.search(line)
            if match:
                module = match.group(1)
                target_file = self._resolve_js_module(module, filepath)
                if target_file:
                    self.dependencies.append(DependencyRelation(
                        source=filepath,
                        target=target_file,
                        relation_type="import",
                        line_number=line_num,
                    ))

    def _resolve_python_module(self, module: str, source_filepath: str) -> Optional[str]:
        """解析 Python 模块名为文件路径"""
        # 跳过标准库和第三方库
        std_libs = {"os", "sys", "re", "json", "pathlib", "datetime", "typing", "subprocess", "argparse"}
        if module.split(".")[0] in std_libs:
            return None

        # 相对导入
        if module.startswith("."):
            source_path = Path(source_filepath)
            level = len(module) - len(module.lstrip("."))
            current_dir = source_path.parent
            for _ in range(level - 1):
                current_dir = current_dir.parent
            module_parts = module.lstrip(".").split(".")
        else:
            module_parts = module.split(".")
            current_dir = self.project_root

        # 尝试查找模块文件
        for i in range(len(module_parts), 0, -1):
            test_path = current_dir / "/".join(module_parts[:i])
            py_file = test_path.with_suffix(".py")
            if py_file.exists():
                try:
                    return str(py_file.relative_to(self.project_root))
                except ValueError:
                    pass
            init_file = test_path / "__init__.py"
            if init_file.exists():
                try:
                    return str(init_file.relative_to(self.project_root))
                except ValueError:
                    pass

        return None

    def _resolve_js_module(self, module: str, source_filepath: str) -> Optional[str]:
        """解析 JavaScript 模块名为文件路径"""
        # 跳过 node_modules
        if not module.startswith(".") and not module.startswith("/"):
            return None

        source_path = Path(source_filepath)
        source_dir = source_path.parent

        # 可能的扩展名
        extensions = [".ts", ".tsx", ".js", ".jsx", ".mjs"]

        # 尝试直接路径
        test_path = source_dir / module
        for ext in extensions:
            if test_path.with_suffix(ext).exists():
                return str(test_path.with_suffix(ext).relative_to(self.project_root))
            if (test_path / "index").with_suffix(ext).exists():
                return str((test_path / "index").with_suffix(ext).relative_to(self.project_root))

        return None

    def build_dependency_graph(self) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """构建依赖图

        返回:
          (dependents_map, dependencies_map)
          - dependents_map: 文件 -> 依赖它的文件列表（谁依赖我）
          - dependencies_map: 文件 -> 它依赖的文件列表（我依赖谁）
        """
        dependents_map: Dict[str, List[str]] = {}
        dependencies_map: Dict[str, List[str]] = {}

        for dep in self.dependencies:
            # dependents: target -> [source]
            if dep.target not in dependents_map:
                dependents_map[dep.target] = []
            if dep.source not in dependents_map[dep.target]:
                dependents_map[dep.target].append(dep.source)

            # dependencies: source -> [target]
            if dep.source not in dependencies_map:
                dependencies_map[dep.source] = []
            if dep.target not in dependencies_map[dep.source]:
                dependencies_map[dep.source].append(dep.target)

        return dependents_map, dependencies_map

    def get_transitive_dependents(self, file: str, dependents_map: Dict[str, List[str]]) -> List[str]:
        """获取传递依赖（所有直接或间接依赖该文件的文件）"""
        visited: Set[str] = set()
        result: List[str] = []

        def dfs(current: str):
            if current in visited:
                return
            visited.add(current)
            if current != file:  # 不包含自己
                result.append(current)
            for dependent in dependents_map.get(current, []):
                dfs(dependent)

        dfs(file)
        return result


# ============================================================================
# 测试文件识别
# ============================================================================

class TestAnalyzer:
    """分析测试文件"""

    TEST_PATTERNS = [
        r"test_.*\.py$",
        r".*_test\.py$",
        r"tests?/.*\.py$",
        r"spec\.ts$",
        r"test\.ts$",
        r"\.spec\.tsx?$",
        r"\.test\.tsx?$",
        r"__tests__/.*",
    ]

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def is_test_file(self, filepath: str) -> bool:
        """判断是否是测试文件"""
        for pattern in self.TEST_PATTERNS:
            if re.search(pattern, filepath):
                return True
        return False

    def find_tests_for_file(self, filepath: str) -> List[str]:
        """查找可能测试该文件的测试文件"""
        tests = []
        path = Path(filepath)

        # 可能的测试文件名模式
        stem = path.stem
        possible_test_names = [
            f"test_{stem}.py",
            f"{stem}_test.py",
            f"{stem}.spec.ts",
            f"{stem}.spec.tsx",
            f"{stem}.test.ts",
            f"{stem}.test.tsx",
        ]

        # 在同目录查找
        for test_name in possible_test_names:
            test_path = path.parent / test_name
            if test_path.exists():
                tests.append(str(test_path.relative_to(self.project_root)))

        # 在 tests 目录查找
        tests_dir = path.parent / "tests"
        if tests_dir.exists():
            for test_name in possible_test_names:
                test_path = tests_dir / test_name
                if test_path.exists():
                    tests.append(str(test_path.relative_to(self.project_root)))

        # 在项目根目录的 tests 目录查找
        root_tests = self.project_root / "tests"
        if root_tests.exists():
            for test_name in possible_test_names:
                test_path = root_tests / test_name
                if test_path.exists():
                    tests.append(str(test_path.relative_to(self.project_root)))

        return tests

    def find_all_tests(self) -> List[str]:
        """查找项目中所有测试文件"""
        tests = []
        for ext in ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx"]:
            for filepath in self.project_root.rglob(ext):
                if self._should_skip(filepath):
                    continue
                rel_path = str(filepath.relative_to(self.project_root))
                if self.is_test_file(rel_path):
                    tests.append(rel_path)
        return tests

    def _should_skip(self, filepath: Path) -> bool:
        skip_dirs = {"node_modules", "venv", ".venv", "__pycache__", ".git", "dist", "build", ".harness"}
        for part in filepath.parts:
            if part in skip_dirs:
                return True
        return False


# ============================================================================
# 主分析器
# ============================================================================

class ImpactAnalyzer:
    """影响范围分析主类"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.git_detector = GitChangeDetector(project_root)
        self.dep_analyzer = DependencyAnalyzer(project_root)
        self.test_analyzer = TestAnalyzer(project_root)

    def analyze(self, scope: str = "all", commit: Optional[str] = None) -> ImpactAnalysis:
        """执行影响范围分析"""
        analysis = ImpactAnalysis()

        # 1. 获取变更文件
        if not self.git_detector.is_git_repo():
            analysis.recommendations.append("警告: 不是 Git 仓库，无法检测变更")
            return analysis

        if scope == "staged":
            changes = self.git_detector.get_staged_changes()
        elif scope == "commit" and commit:
            changes = self.git_detector.get_commit_changes(commit)
        else:
            changes = self.git_detector.get_all_changes()

        analysis.changed_files = changes

        if not changes:
            analysis.recommendations.append("没有检测到代码变更")
            return analysis

        # 2. 分析依赖关系
        self.dep_analyzer.analyze_project()
        dependents_map, _ = self.dep_analyzer.build_dependency_graph()

        # 3. 计算受影响文件
        for change in changes:
            filepath = change.path

            # 直接依赖
            direct_deps = dependents_map.get(filepath, [])
            if direct_deps:
                analysis.direct_dependents[filepath] = direct_deps

            # 传递依赖
            transitive_deps = self.dep_analyzer.get_transitive_dependents(filepath, dependents_map)
            if transitive_deps:
                analysis.transitive_dependents[filepath] = transitive_deps

        # 4. 识别受影响的测试
        all_affected_files = set()
        for change in changes:
            all_affected_files.add(change.path)
            all_affected_files.update(analysis.direct_dependents.get(change.path, []))
            all_affected_files.update(analysis.transitive_dependents.get(change.path, []))

        # 找出这些文件中的测试
        for filepath in all_affected_files:
            if self.test_analyzer.is_test_file(filepath):
                analysis.affected_tests.append(filepath)

        # 为每个变更文件建议测试
        test_suggestions: List[TestSuggestion] = []
        for change in changes:
            if change.change_type == ChangeType.DELETED:
                continue
            suggested_tests = self.test_analyzer.find_tests_for_file(change.path)
            for test_file in suggested_tests:
                if test_file not in analysis.affected_tests:
                    analysis.affected_tests.append(test_file)
                    test_suggestions.append(TestSuggestion(
                        test_file=test_file,
                        priority="high",
                        reason=f"{change.path} 被修改，相关测试需要验证",
                        related_changes=[change.path],
                    ))

        # 5. 评估风险等级
        analysis.risk_level = self._assess_risk(analysis)

        # 6. 生成建议
        analysis.recommendations = self._generate_recommendations(analysis)

        return analysis

    def _assess_risk(self, analysis: ImpactAnalysis) -> str:
        """评估风险等级"""
        score = 0

        # 变更文件数量
        num_changes = len(analysis.changed_files)
        if num_changes >= 10:
            score += 3
        elif num_changes >= 5:
            score += 2
        elif num_changes >= 2:
            score += 1

        # 受影响文件数量
        total_affected = set()
        for deps in analysis.direct_dependents.values():
            total_affected.update(deps)
        for deps in analysis.transitive_dependents.values():
            total_affected.update(deps)

        if len(total_affected) >= 20:
            score += 3
        elif len(total_affected) >= 10:
            score += 2
        elif len(total_affected) >= 5:
            score += 1

        # 是否有核心文件变更
        core_patterns = [r"^src/", r"^lib/", r"^core/", r"^api/", r"^service/", r"^utils/"]
        for change in analysis.changed_files:
            for pattern in core_patterns:
                if re.search(pattern, change.path):
                    score += 2
                    break

        # 测试覆盖情况
        if not analysis.affected_tests:
            score += 2
        elif len(analysis.affected_tests) < num_changes:
            score += 1

        if score >= 7:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(self, analysis: ImpactAnalysis) -> List[str]:
        """生成建议列表"""
        recommendations = []

        # 测试建议
        if analysis.affected_tests:
            recommendations.append(f"建议运行以下测试: {', '.join(analysis.affected_tests[:5])}")
            if len(analysis.affected_tests) > 5:
                recommendations.append(f"还有 {len(analysis.affected_tests) - 5} 个测试需要运行")
        else:
            recommendations.append("警告: 没有找到相关测试，建议手动验证")

        # 风险提示
        if analysis.risk_level == "high":
            recommendations.append("⚠️  高风险变更，建议全面回归测试")
            recommendations.append("   建议: 分阶段提交，先提交核心变更")
        elif analysis.risk_level == "medium":
            recommendations.append("中等风险变更，建议重点测试受影响模块")

        # 受影响文件提示
        total_dependents = set()
        for deps in analysis.transitive_dependents.values():
            total_dependents.update(deps)
        if total_dependents:
            recommendations.append(f"共有 {len(total_dependents)} 个文件间接受影响")

        return recommendations


# ============================================================================
# 输出格式化
# ============================================================================

def format_analysis(analysis: ImpactAnalysis, format_type: str = "text") -> str:
    """格式化分析结果"""
    if format_type == "json":
        return json.dumps({
            "changed_files": [
                {"path": c.path, "type": c.change_type.value}
                for c in analysis.changed_files
            ],
            "direct_dependents": analysis.direct_dependents,
            "transitive_dependents": analysis.transitive_dependents,
            "affected_tests": analysis.affected_tests,
            "risk_level": analysis.risk_level,
            "recommendations": analysis.recommendations,
        }, indent=2, ensure_ascii=False)

    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║              代码变更影响范围分析报告                          ║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")

    # 变更文件
    lines.append("📋 变更文件:")
    if analysis.changed_files:
        type_icons = {
            ChangeType.ADDED: "➕",
            ChangeType.MODIFIED: "✏️ ",
            ChangeType.DELETED: "🗑️ ",
            ChangeType.RENAMED: "📦",
        }
        for change in analysis.changed_files:
            icon = type_icons.get(change.change_type, "❓")
            lines.append(f"  {icon} {change.path}")
    else:
        lines.append("  (无变更)")
    lines.append("")

    # 直接依赖
    if analysis.direct_dependents:
        lines.append("🔗 直接受影响的文件:")
        for changed_file, dependents in analysis.direct_dependents.items():
            lines.append(f"  {changed_file}:")
            for dep in dependents[:5]:
                lines.append(f"    → {dep}")
            if len(dependents) > 5:
                lines.append(f"    ... 还有 {len(dependents) - 5} 个")
        lines.append("")

    # 传递依赖汇总
    total_transitive = set()
    for deps in analysis.transitive_dependents.values():
        total_transitive.update(deps)
    if total_transitive:
        lines.append(f"🌐 间接受影响的文件: {len(total_transitive)} 个")
        lines.append("")

    # 受影响的测试
    lines.append("🧪 建议运行的测试:")
    if analysis.affected_tests:
        for test in analysis.affected_tests:
            lines.append(f"  ✅ {test}")
    else:
        lines.append("  ⚠️  未找到相关测试，建议手动验证")
    lines.append("")

    # 风险等级
    risk_icons = {
        "low": "🟢 低风险",
        "medium": "🟡 中等风险",
        "high": "🔴 高风险",
    }
    lines.append(f"⚠️  风险等级: {risk_icons.get(analysis.risk_level, analysis.risk_level)}")
    lines.append("")

    # 建议
    lines.append("💡 建议:")
    for rec in analysis.recommendations:
        lines.append(f"  • {rec}")
    lines.append("")

    # 测试命令
    if analysis.affected_tests:
        lines.append("🧪 快速运行命令:")
        if any(t.endswith(".py") for t in analysis.affected_tests):
            lines.append(f"  python -m pytest {' '.join(analysis.affected_tests[:5])} -v")
        if any(t.endswith((".ts", ".tsx", ".js", ".jsx")) for t in analysis.affected_tests):
            lines.append(f"  npm test -- {' '.join(analysis.affected_tests[:5])}")
        lines.append("")

    return "\n".join(lines)


def format_test_suggestions(analysis: ImpactAnalysis) -> str:
    """仅输出测试建议"""
    if not analysis.affected_tests:
        return "# 未找到相关测试，建议手动验证变更\n"

    lines = []
    lines.append("# 测试建议")
    lines.append("")
    lines.append("## 需运行的测试")
    lines.append("")
    for test in analysis.affected_tests:
        lines.append(f"- [ ] {test}")
    lines.append("")
    lines.append("## 运行命令")
    lines.append("")
    if any(t.endswith(".py") for t in analysis.affected_tests):
        py_tests = [t for t in analysis.affected_tests if t.endswith(".py")]
        lines.append(f"```bash")
        lines.append(f"python -m pytest {' '.join(py_tests)} -v")
        lines.append(f"```")
        lines.append("")
    if any(t.endswith((".ts", ".tsx", ".js", ".jsx")) for t in analysis.affected_tests):
        js_tests = [t for t in analysis.affected_tests if t.endswith((".ts", ".tsx", ".js", ".jsx"))]
        lines.append(f"```bash")
        lines.append(f"npm test -- {' '.join(js_tests)}")
        lines.append(f"```")
    return "\n".join(lines)


# ============================================================================
# 主入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="代码变更影响范围分析器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 分析所有变更
  %(prog)s --staged                 # 分析已暂存变更
  %(prog)s --commit HEAD~1          # 分析最近一次提交
  %(prog)s --json                   # JSON 格式输出
  %(prog)s --suggest-tests          # 仅输出测试建议
        """,
    )

    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument("--staged", action="store_true", help="分析已暂存变更")
    scope_group.add_argument("--commit", metavar="REF", help="分析指定提交的变更")

    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="JSON 格式输出")
    output_group.add_argument("--suggest-tests", action="store_true", help="仅输出测试建议")

    args = parser.parse_args()

    # 确定项目根目录
    project_root = Path.cwd()
    while not (project_root / ".git").exists() and project_root.parent != project_root:
        project_root = project_root.parent

    # 执行分析
    analyzer = ImpactAnalyzer(project_root)

    if args.commit:
        analysis = analyzer.analyze(scope="commit", commit=args.commit)
    elif args.staged:
        analysis = analyzer.analyze(scope="staged")
    else:
        analysis = analyzer.analyze(scope="all")

    # 输出结果
    if args.json:
        print(format_analysis(analysis, format_type="json"))
    elif args.suggest_tests:
        print(format_test_suggestions(analysis))
    else:
        print(format_analysis(analysis))

    # 根据风险等级返回退出码
    if analysis.risk_level == "high":
        sys.exit(2)
    elif analysis.risk_level == "medium":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
